#include <algorithm>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>

#include <unitree/robot/g1/agv/g1_agv_client.hpp>

namespace {

volatile std::sig_atomic_t g_running = 1;

struct Command {
  std::uint64_t sequence = 0;
  float vx = 0.0F;
  float vyaw = 0.0F;
  float lift_vz = 0.0F;
  std::chrono::steady_clock::time_point received = std::chrono::steady_clock::now();
};

void SignalHandler(int) { g_running = 0; }

float Clamp(float value, float low, float high) {
  return std::max(low, std::min(high, value));
}

bool ParseCommand(const std::string &line, Command *command) {
  Command parsed;
  std::istringstream input(line);
  if (!(input >> parsed.sequence >> parsed.vx >> parsed.vyaw >> parsed.lift_vz)) {
    return false;
  }
  std::string trailing;
  if (input >> trailing) {
    return false;
  }
  if (!std::isfinite(parsed.vx) || !std::isfinite(parsed.vyaw) ||
      !std::isfinite(parsed.lift_vz)) {
    return false;
  }
  parsed.vx = Clamp(parsed.vx, -1.5F, 1.5F);
  parsed.vyaw = Clamp(parsed.vyaw, -0.6F, 0.6F);
  parsed.lift_vz = Clamp(parsed.lift_vz, -1.0F, 1.0F);
  parsed.received = std::chrono::steady_clock::now();
  *command = parsed;
  return true;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 2 || argc > 3) {
    std::cerr << "Usage: g1d_agv_bridge network_interface [watchdog_ms]\n";
    return 2;
  }

  const std::string network_interface = argv[1];
  int watchdog_ms = 300;
  if (argc == 3) {
    try {
      watchdog_ms = std::stoi(argv[2]);
    } catch (...) {
      std::cerr << "Invalid watchdog_ms: " << argv[2] << '\n';
      return 2;
    }
  }
  if (watchdog_ms < 100 || watchdog_ms > 5000) {
    std::cerr << "watchdog_ms must be in [100, 5000]\n";
    return 2;
  }

  std::signal(SIGINT, SignalHandler);
  std::signal(SIGTERM, SignalHandler);

  unitree::robot::ChannelFactory::Instance()->Init(0, network_interface);
  unitree::robot::g1::AgvClient agv;
  agv.SetTimeout(3.0F);
  agv.Init();

  std::mutex command_mutex;
  Command latest;
  std::thread reader([&]() {
    std::string line;
    while (g_running != 0 && std::getline(std::cin, line)) {
      Command parsed;
      if (!ParseCommand(line, &parsed)) {
        std::cerr << "Ignoring malformed command: " << line << '\n';
        continue;
      }
      std::lock_guard<std::mutex> lock(command_mutex);
      latest = parsed;
    }
    g_running = 0;
  });
  reader.detach();

  std::cerr << "g1d_agv_bridge ready on " << network_interface
            << ", watchdog=" << watchdog_ms << " ms\n";

  const auto period = std::chrono::milliseconds(50);
  while (g_running != 0) {
    const auto loop_start = std::chrono::steady_clock::now();
    Command command;
    {
      std::lock_guard<std::mutex> lock(command_mutex);
      command = latest;
    }

    const auto age_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            loop_start - command.received)
                            .count();
    if (age_ms > watchdog_ms) {
      command.vx = 0.0F;
      command.vyaw = 0.0F;
      command.lift_vz = 0.0F;
    }

    const std::int32_t move_ret = agv.Move(command.vx, 0.0F, command.vyaw);
    const std::int32_t height_ret = agv.HeightAdjust(command.lift_vz);
    if (move_ret != 0 || height_ret != 0) {
      std::cerr << "SDK call failed at sequence " << command.sequence
                << ": Move=" << move_ret << " HeightAdjust=" << height_ret << '\n';
    }

    std::this_thread::sleep_until(loop_start + period);
  }

  agv.Move(0.0F, 0.0F, 0.0F);
  agv.HeightAdjust(0.0F);
  return 0;
}
