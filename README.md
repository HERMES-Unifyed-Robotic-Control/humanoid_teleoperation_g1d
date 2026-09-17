# XR Teleoperate G1-D

可直接部署的 G1-D XR 遥操与数采工程。目录已包含官方 XR 遥操源码、G1-D URDF/mesh、相机客户端，以及本次加入的手柄映射、腰部 Pitch 控制和完整操作输入记录；运行时不依赖 `/unitree/module/unitree_eai/xr_teleoperate`，也无需再打补丁。

## 控制键位

| Pico 输入 | G1-D 输出 |
|---|---|
| 左摇杆 Y | 底盘前进/后退 `vx` |
| 左摇杆 X | 底盘原地旋转 `vyaw` |
| 右摇杆 Y | 升降架速度 `vz` |
| 右摇杆 X | 腰部俯仰 `waist_pitch` |
| 左/右 Grip | 左/右臂接管 |
| 左/右控制器位姿 | 左/右臂重定向目标 |
| 左/右 Trigger | 左/右 Dex1 开闭比例 |
| 右手柄 A | 启动遥操（等同键盘 `R`） |
| 左手柄 Y | 开始/结束并保存 episode（等同键盘 `S`） |
| 右手柄 B | 结束遥操（等同键盘 `Q`） |
| 键盘 `R` / `S` / `Q` | 建立遥操 / 开关 episode / 退出 |

G1-D 是双轮差速底盘，控制动作只有前后速度与偏航角速度，不下发横移速度。

## 项目树

```text
xr_teleoperate_g1d/
├── assets/g1_D/                # G1-D URDF 和 mesh
├── teleop/                     # 可直接运行的 XR 双臂、Dex1、底盘、升降源码
│   ├── robot_control/
│   ├── teleimager/
│   ├── televuer/
│   ├── utils/
│   └── teleop_hand_and_arm.py
├── xr_teleoperate_g1d/         # 标准输入、映射、驱动和 JSONL 记录器
├── bridge/                     # 最新 SDK2 AgvClient C++ 后端
├── tests/
├── docs/
├── launch_g1d.sh               # G1-D 默认启动入口
├── requirements.txt
└── pyproject.toml
```

## 部署和启动

将整个目录复制到机器人，例如 `/home/unitree/xr_teleoperate_g1d`，然后安装 Python 依赖：

```bash
cd /home/unitree/xr_teleoperate_g1d
/home/unitree/miniconda3/envs/tv/bin/python -m pip install -e .
/home/unitree/miniconda3/envs/tv/bin/python -m pip install -r requirements.txt
chmod +x launch_g1d.sh
```

这台 G1-D 的 Dex1 夹爪是接在机器人低层总线上的内部电机（`rt/lowstate` 槽位 31/33），不需要启动外置串口 `dex1_1_service`。启动器默认使用 `--ee=dex1_internal`。确认一次外置服务不会抢占或反复报错：

```bash
sudo systemctl disable --now dex1_gripper.service
systemctl is-active dex1_gripper.service || true
```

开始 G1-D XR 遥操数采：

```bash
cd /home/unitree/xr_teleoperate_g1d
./launch_g1d.sh \
  --record \
  --task-name g1d_xr_test \
  --network-interface eth0
```

启动器默认使用机器人已有的 `/home/unitree/miniconda3/envs/tv/bin/python`，参数为 controller、immersive 双目画面、G1、**内部 Dex1**、mobile_lift、腰部 Pitch 和 headless；PICO 可访问的 WebRTC 地址固定为机器人无线口 `192.168.10.104:60001`。追加参数会继续传给主程序。需要使用其他环境时可设置 `PYTHON_BIN=/path/to/python`；需要透视模式时设置 `DISPLAY_MODE=pass-through`。只有连接了独立串口 Dex1 板卡时，才设置 `EE_MODE=dex1` 并确保对应服务已经正常运行。

PICO 端首次先分别访问 `https://192.168.10.104:8012` 和 `https://192.168.10.104:60001` 并接受证书，再打开启动器打印的 `https://vuer.ai?ws=wss://192.168.10.104:8012`；若 PICO 无公网访问，使用本地备用地址。不要同时打开多个 XR 页面。等待终端出现 `websocket is connected` 后，可完全使用手柄操作：右 A 启动；左 Y 开始一个 episode，再按左 Y 停止并保存，确认播报保存完成后可继续按左 Y 录制下一个 episode；右 B 结束整个遥操。机器人扬声器默认使用普通话播报准备、按键、采集、保存和退出状态。中文文本使用“诶键、比键、歪键”，避免中文音色跳过拉丁字母。可用 `VOICE_LANGUAGE=zh`、`VOICE_LANGUAGE=en` 或 `VOICE_LANGUAGE=bilingual` 选择语言；不需要语音时追加 `--no-voice`。键盘 `R/S/Q` 继续保留。

## 数采内容

官方字段继续保存图像、双臂关节、末端位姿、Dex1 电机状态/目标、底盘、升降和腰部反馈。本项目还在每一帧中加入：

- `states.xr`：四个摇杆轴、Grip、Trigger、按钮、头显与左右控制器 4×4 位姿、motion-ready 和时间戳；
- `actions.operator.chassis`：实际下发的 `vx/vy/vyaw`；
- `actions.operator.lift`：实际下发的 `vz`；
- `actions.operator.waist`：腰部 Pitch 位置目标；
- `actions.operator.dex1`：左右夹爪 0–1 闭合比例；
- `actions.operator.arm`：双臂接管量和左右腕部目标位姿。

现场 IP、PICO 配网、各终端命令及启停顺序见 [网络拓扑与数采运行手册](docs/network_runbook.md)。字段定义见 [数采结构](docs/data_schema.md)，源码修改点见 [直接集成说明](docs/official_integration.md)，机器人程序与 SDK2 结论见 [G1-D 程序梳理](docs/g1d_findings.md)。

## 离线验证和 SDK2 后端

```bash
python -m unittest discover -s tests -v
python -m xr_teleoperate_g1d --source demo --driver dry-run --record logs/demo.jsonl
```

`bridge/g1d_agv_bridge.cpp` 提供最新 SDK2 的 `AgvClient::Move()`、`HeightAdjust()` 和 300 ms 指令看门狗。它是替代底盘/升降 Python DDS 发布端的可选后端，两者不能在真机上同时运行。
