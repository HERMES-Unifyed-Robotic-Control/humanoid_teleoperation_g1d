# G1-D 现有程序与链路梳理

## 机器人上的主程序

机器人地址为 `unitree@192.168.123.164`。当前与任务直接相关的目录如下：

```text
/unitree/module/unitree_eai/
├── agent/unitree_eai_agent
└── xr_teleoperate/
│   ├── assets/g1_D/g1_d.urdf
│   └── teleop/
│       ├── teleop_hand_and_arm.py
│       ├── robot_control/
│       │   ├── mobile_control.py
│       │   ├── robot_arm.py
│       │   ├── robot_arm_ik.py
│       │   └── robot_hand_unitree.py
│       └── utils/
│           ├── instruction_map.py
│           └── episode_writer.py

/home/unitree/unitree_eai_environment/service/dex1_1_service/
├── bin/dex1_1_gripper_server
├── setup_autostart.sh
└── README.md
```

当前 `teleop_hand_and_arm.py` 已支持：

- `--base-type mobile_lift`：同时启用底盘和升降架；
- `--ee dex1`：外置 Dex1.1，通过独立串口转 DDS 服务控制；
- `--ee dex1_internal`：Dex1 电机作为 G1-D 低层电机的一部分控制；本机应使用这一模式；
- `--input-mode controller`：Pico 控制器位姿驱动双臂，Trigger 驱动 Dex1；
- `--record`：相机、手臂、末端、机体、升降和底盘一起写入 episode。

因此之前“看不到底盘和升降驱动”的原因主要是实现不在入口文件里：底盘/升降位于 `robot_control/mobile_control.py`，手柄映射位于 `utils/instruction_map.py`，采集拼装位于入口脚本约 490 行之后。G1-D 的 Dex1 还可以直接走内部低层电机槽位，不需要外置串口服务。

## 底盘与升降的两套接口

机器人现有 XR 程序使用 Python DDS：

| 功能 | 命令 topic | 状态 topic | 消息 |
|---|---|---|---|
| 升降 | `rt/cmd_hispeed` | `rt/hispeed_state` | `Point32_` |
| 底盘 | `rt/cmd_vel_no_limit` | `rt/slamware_ros_sdk_server_node/odom` | `Twist_` / `Odometry_` |

`mobile_control.py` 把升降速度写入 `Point32_.z`，从状态的 `Point32_.y` 读取高度、从 `.z` 读取速度。底盘动作只有 `[vx, vyaw]` 两维。

最新 `/home/unitree/unitree_sdk2`（检查时 commit `9754cd1`）新增了正式 G1-D API：

```text
example/g1/g1d/
├── g1_agv_client_example.cpp
├── g1d_arm_example.cpp
├── g1d_height_control.cpp
└── gamepad.hpp
```

已编译程序位于 `build/bin/`。`g1_agv_client_example` 会无限循环产生正弦底盘/升降命令，只适合架空轮组后的接口验证，不应作为遥操启动程序。`g1d_height_control <网卡> <目标高度米>` 使用高度状态和 PD 控制到目标高度。

新接口 `unitree::robot::g1::AgvClient` 的约束是：

- `Move(vx, 0, vyaw)`：`vx` 最大 ±1.5 m/s，`vyaw` 最大 ±0.6 rad/s，`vy` 不支持；
- `HeightAdjust(vz)`：归一化输入 ±1，对应立柱最大约 ±76.5 mm/s；
- 服务名为 `agv`，API 版本 `1.0.0.1`，Move/HeightAdjust API ID 为 1001/1002。

本项目默认限速 `vx=0.2 m/s`、`vyaw=0.6 rad/s`、`lift=1.0`，并在 C++ bridge 中再次按 SDK 机械范围限幅和失联停机。

## `dex1_1_service` 如何工作

`dex1_1_service` 是 serial-to-DDS 网关，不负责 Pico 映射或夹爪轨迹规划。服务进程扫描 `/dev/ttyUSB*` 和 `/dev/ttyCH343USB*`，识别 M4010 电机，约 2 kHz 地在串口协议与 DDS 之间转换。默认电机 ID 0 为右夹爪、ID 1 为左夹爪。

DDS topic 为：

| 方向 | 左夹爪 | 右夹爪 |
|---|---|---|
| 命令 | `rt/dex1/left/cmd` | `rt/dex1/right/cmd` |
| 状态 | `rt/dex1/left/state` | `rt/dex1/right/state` |

真正的控制算法在 `robot_hand_unitree.py::Dex1_1_Gripper_Controller`：它读取 Trigger/捏合值，将夹爪范围映射到电机位置约 0–5.4 rad，用当前 DDS 状态把单周期变化限制在 ±0.18 rad，再通过三点加权滤波，以 200 Hz 发布 `MotorCmds_`。命令参数为 `kp=5.0`、`kd=0.05`，状态和动作各记录左右两个标量。

服务检查命令：

```bash
sudo systemctl status dex1_gripper.service
sudo journalctl -u dex1_gripper.service -f
```

检查时这台机器人有四个 `/dev/ttyCH343USB0..3` 设备，但 `dex1_1_gripper_server` 无法收到电机 ID 0/1 的回复。进一步订阅 `rt/lowstate` 后确认总电机数为 35，槽位 31（左 Dex1）和 33（右 Dex1）都有非零温度及实时位置/速度反馈。因此这些夹爪是 G1-D 内部总线电机，外置串口服务不适用于当前接线，应保持停用：

```bash
sudo systemctl disable --now dex1_gripper.service
```

只有在更换为独立串口 Dex1 板卡后，才使用 `--ee dex1` 及 `dex1_1_gripper_server --network eth0`。

## 当前 XR 映射与本项目映射

G1-D 原装遥控器和机器人 `instruction_map.py` 的轴分工为：左摇杆 Y 前后、左摇杆 X 旋转、右摇杆 Y 升降、右摇杆 X 腰部俯仰。机器人入口记录的 body action 也按 `[-left_y, -left_x, -right_x] * 0.3` 保存。

最新 SDK2 `g1d_arm_example.cpp` 明确把 `WaistYaw=12` 和 `WaistPitch=14` 标为 G1-D 的两个有效腰关节，`WaistRoll=13` 无效。宇树产品参数也给出腰部 Z 轴旋转与 Y 轴俯仰两个自由度。

原始 XR 代码有一处错位：`teleop_hand_and_arm.py` 把右摇杆 X 交给 `--use-waist`，但 `robot_arm.py::G1_29_Waist_JointIndex` 选的是 `WaistYaw=12`。本目录源码已直接改到 `WaistPitch=14`，把右 X 作为俯仰增量输入，并按约 `-2.5°～135°` 限制位置目标。

## 推荐运行顺序

1. 确认机器人 `eth0` 和 sys01 在 `192.168.123.0/24`，PICO 连接 `TP-LINK_413` 并在 `192.168.10.0/24`。
2. 确认 `teleimager.service` 和内部 Dex1 反馈在线（槽位 31/33）。
3. 确认 `unitree_eai_agent -v` 至少为 1.4.1，并让 EAI 平台显示设备在线；当前实机为 v1.5.0，agent 进程正在运行。
4. 启动本目录的 `launch_g1d.sh --record --task-name <任务名> --network-interface eth0`；该入口默认使用 `--ee dex1_internal`，并检查 60000 相机配置端口以及 8012 是否被旧进程占用。
5. 等待终端出现 `EpisodeWriter initialized successfully` 和 `Please enter the start signal`，PICO 再打开 `https://vuer.ai?ws=wss://192.168.10.104:8012`，进入 Virtual Reality 并完成房间标定。
6. 用 `R/S/Q` 完成连接、episode 开关与退出。

调试阶段先运行官方 Python DDS 后端。SDK2 bridge 用于后续统一到正式 `AgvClient`，切换时停止官方 `mobile_control.py` 的发布端，避免双发布者争抢控制。
