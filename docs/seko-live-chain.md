# Seko 实打链路（2026-09-04）

凭证：用户 Bearer 只进进程。报告不收录 token。用完请作废。
画布：2095808097188225026

## 打通条件
- Header：Authorization Bearer + Clientid + X-User-Id + Timestamp
- POST 体 WASM encrypt，Content-Type 必须 application/json（text/plain 业务 500）
- FREE：seedream_v50_pro + imageQuality=2 直接 500；Seedance 2.5 受理后失败

## 1. 文生图 SUCCESS
POST /seko-api/seko-canvas/v1/canvas-node/gen-image
imageModel=z-image，prompt=写实，白色家用机器人在橡木地板上，清晨阳光轮廓光，温馨现代卧室，无水印
nodeId=2095816836949626881 扣 1 分
url=https://seko-resource.sensetime.com/seko/algo-gen/creations/1d52f2b5bf1d4cd8aef9986f52082098.png

## 2. 图生图 SUCCESS
同一接口，imageModel=auto → volc_jimeng_v40，refNodeIds=[金发女郎 2095812151255670785]
prompt=同一位金发女郎站在温馨现代卧室窗边，清晨阳光，写实，全身，无水印
nodeId=2095817645569495042 扣 1 分
url=https://seko-resource.sensetime.com/STS/seko/prod/guodong-transformer/output/4e0cfff6-a462-4316-a9e5-2cda7961d5ba/021788516840191f7b571b3147c8053e664bd4ad440a263e8ff43_0.jpeg
z-image+参考两次 GENERATING_FAILED。

## 3. 连线生视频 SUCCESS
POST /v1/canvas-node/gen-video
firstFrameNodeId=2095816836949626881 videoModel=viduq2-turbo duration=5
nodeId=2095817374277718018 扣 10 分
url=https://seko-resource.sensetime.com/STS/seko/prod/guodong-transformer/output/4986cfc2-7b0f-4b34-bcbf-28a2854ed414/video.mp4
Seedance 2.5 同结构失败（FREE 会员关掉高质量视频）。
