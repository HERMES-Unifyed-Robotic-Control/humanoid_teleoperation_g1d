# 遥操数采字段

每个控制周期都应形成同一时间基准下的一帧，至少包含原始 XR 输入、下发动作、机器人反馈和图像引用。`Recorder` 的 JSONL 结构如下：

```text
frame
├── sequence
├── timestamp_ns
├── xr
│   ├── motion_ready
│   ├── left_x, left_y, right_x, right_y
│   ├── left_trigger, right_trigger
│   ├── left_grip, right_grip
│   ├── left_pose[4][4], right_pose[4][4], headset_pose[4][4]
│   └── buttons
├── actions
│   ├── chassis: vx, vy=0, vyaw
│   ├── lift: vz
│   ├── waist: pitch_velocity
│   ├── dex1: enabled, left_closed_ratio, right_closed_ratio
│   └── arm: motion_ready, left_active, right_active, target
├── states
│   ├── chassis: vx, vyaw
│   ├── lift: height, vz
│   ├── waist: pitch, pitch_velocity
│   ├── dex1: left_q, right_q
│   ├── arm/body: qpos, qvel, torque
│   └── cameras: head, left_wrist, right_wrist
└── safety
    ├── motion_ready
    └── stop_commanded
```

EpisodeWriter 会记录三路图像、左右臂关节与末端位姿、Dex1 状态/动作、机体关节、升降高度/速度以及底盘 `[vx, vyaw]` 状态/动作。controller 模式的兼容 `body.qpos` 三维依次对应底盘前后、底盘旋转和腰部俯仰。本目录源码还把摇杆、按钮、Grip、Trigger、头显及控制器原始位姿写入 `states.xr`，并把实际控制目标写入 `actions.operator`，因此可以区分操作者输入、IK 结果和机器人反馈。

Trigger 在本项目内统一为 `0=全开、1=全闭`。机器人 TeleVuer 的旧值可能是 `10=松开、0=按满`，接入时必须先归一化，不能把两种范围直接混用。Dex1 的数据集动作建议同时保留：

- `closed_ratio`：跨硬件的 0–1 操作语义；
- `motor_q`：真正发布到 DDS 的约 0–5.4 rad 目标；
- `state_q`：夹爪服务返回的实际电机位置。

时间戳优先使用 XR SDK 的纳秒时间，并在图像、DDS 状态和动作入帧时记录各自源时间戳。若暂时只能取得主循环时间，至少保留 `timestamp_ns` 和递增 `sequence`，并避免事后按文件名推断同步关系。
