# 比亚迪汉 EV：红色原版 / 滴滴概念皮肤（白车修订第二版）

为 GoTogether 制作的独立车辆图片素材包。车型为同代 Dragon Face 汉 EV 的 AI 生成演绎，不是汉 L，也不是可旋转的 3D 模型或精确工程复刻。

## 交付文件

| 文件 | 用途 |
|---|---|
| `static/vehicles/han/default.webp` | 红色普通版，网页推荐素材 |
| `static/vehicles/han/didi.webp` | 珍珠白＋橙色标记/深灰「滴滴出行」门贴，删除大块橙色下包围 |
| `png/han-default.png`、`png/han-didi.png` | 对应透明 PNG |
| `sources/han-red-source.png` | 红色原始生成图，1513×1040 |
| `sources/han-didi-source.png` | 基于红色母版编辑的白橙原图，1512×1040 |
| `preview/han-two-variants.jpg` | 两版并排预览，背景为展示用 |
| `preview/han-contact-sheet.jpg` | 浅色、深色、棋盘背景及 180px 缩略验收图 |
| `docs/*-prompt.txt` | 初版生成/编辑及第二版修订的完整提示词 |
| `docs/export-qa.json`、`manifest.json` | 导出参数、透明度与文件校验记录 |
| `sources.json` | 车型、视觉参考与资源路径 |
| `export_assets.py` | 可重复的尺寸/格式导出与预览生成脚本 |

两张成品均为 **640×440、真实 Alpha 透明**。WebP 使用无损编码，解码后与 PNG 像素完全一致。车头朝左下，前侧 3/4 轻俯视，保留轻微接触阴影。两版使用同一裁切框、缩放尺寸和偏移，不分别自动居中。

红色先作为母版生成，白车由内置 image_gen 编辑母版，再根据真实滴滴车辆门贴参考修订。第二版采用更小的橙色标记＋深灰文字，恢复连续白色门板与原厂风格深色底边。详见 docs/didi-revision-notes.md。AI 编辑仍存在极细微轮廓/阴影变化，不承诺逐像素相同；导出后高 Alpha 主体轮廓交并比为 99.27%，两版位置与轮距在 UI 尺寸下基本一致。未用后期重新画车身或拼接文字。

已检查浅色/深色/棋盘背景和 180px 宽度。640px 成品能读出「滴滴出行」；180px 时橙色标记仍可辨识，但门贴文字很小，界面应另配可访问的文字标签，不能仅靠车门文字传达车型或皮肤名称。

## 接入 GoTogether：完整检查清单

**本包只包含素材与接入说明，未修改仓库、数据库或部署。红色 PNG、WebP 和源图与首版逐字节一致。** 以下依据 2026-10-20 只读检查的 GitHub 默认分支 master，提交 `4b6762b1f91f13a5260935cdd10fd0ff762b4a03`，数据库版本 v9。没有检查用户本地未推送内容、真实数据库或运行页面。接入前必须重读目标分支与 AGENTS.md；以实际代码为准。

### 1. 合并文件，登记车型和外观

- 车型 ID 为 `han`，外观 ID 为 `default`、`didi`。
- 将本包 `static/vehicles/han/` 合并到项目同路径，勿覆盖整个 `static/` 目录。
- 可将原图、提示词、来源和导出参数保存到项目的 `design/han-skins-20261020/`，更新 `design/README.md`。
- `store.py` 的 `VEHICLE_APPEARANCES` 增加 `'han': '比亚迪汉'`；保留项目实际已有车型与默认 `su7`。
- `VEHICLE_COLORS` 增加 `'han': {'default': '红色原版', 'didi': '滴滴出行'}`。现有 `vehicle_image()` 按登记值即可得到 `vehicles/han/default.webp`、`vehicles/han/didi.webp`。未登记 `didi` 会回退到 `default`。

### 2. 模板、皮肤字段、校验必须同步

当前 `templates/travel.html` 和 `store.py` 都将“皮肤”分支硬编码为 `yadea`。**只加字典不足以完成接入。**

- 将皮肤分支扩展为可按车型配置；汉使用车辆缩略图选皮肤，不尝试读取 `han/swatches/` 色卡目录。
- 推荐汉使用独立表单字段 `skin_han`，雅迪继续使用 `skin`，SU7 继续使用 `color`；模板与后端用同一车型→字段映射。不要让汉和雅迪的单选组共用 `name="skin"`，否则会互相取消选择。
- 后端 `save_vehicle()` 按汉对应字段读取、校验 `default`/`didi`；拒绝或安全回退非法值。保持缺字段时保留已有皮肤、换车型时回到默认皮肤的行为。
- 已选项、预览、错误回显都使用对应字段。编辑记录时须回退读取数据库 `color`：现有 `app.py` 把车辆记录合入 `values`，数据库没有独立 `skin` 列。
- 美团专属提示仅留给雅迪；汉可显示“滴滴出行概念皮肤”，不暗示真实营运资质或合作。
- `static/app.js` 已按 `data-color-picker` / `data-color-image` / `data-vehicle-preview` 通用处理，原则上不需要汉的路径特判，但必须测试汉↔雅迪↔SU7 来回切换。
- 车辆卡片/图片替代文本显示正确车型和外观名称，沿用 640×440 画布；窄屏约 180px 要有界面文字标签。

### 3. 新建库 CHECK 与旧库迁移，二者都要改

- `schema.sql` 的 `vehicles.appearance CHECK` 目前只允许 `phantom, tricycle, su7, v800, kart, yadea, horse-carriage, wuling, dayun, mega`，需要追加 `han`，同时保留实际目标分支其他已加入车型（例如另行接入的 CT5）。
- `color` 没有枚举 CHECK，滴滴皮肤继续保存在 `color='didi'`，不需新增 `skin` 列。
- **必须新增数据库迁移扩展旧表 CHECK，不能只改 schema.sql，不能重写已执行迁移。**
- 可参照现有 `migrations/migration_9.sql` 的保留车辆 ID 方式：新增带完整车型枚举的 `appearance_vN` 临时列 → 复制旧值 → 删除旧列 → 重命名 → 设置 `PRAGMA user_version=N`。保留车辆 ID、乘客关联、原有外观和颜色值；采用现有事务与 SQLite ≥3.35 检查。
- 检查时远端迁移仅到 v9，因此当时下一个编号是 10；**不要硬编码或覆盖 migration_10.sql**。如果 CT5 或其他改动已占用该版本，使用实际下一个版本并保留前一迁移新增的枚举。

### 4. 初始化升级入口与版本同步

实际入口为 `store.py` 的 `initialize()`，没有名为 `initializeVersion` 的独立函数。

- 同步其旧版本兼容分支、迁移循环终点与目标版本校验。
- 仅举例：若接入前核实目标确为 v10，则兼容旧版本 1–9，迁移循环为 `range(version + 1, 11)`，目标校验为 `version != 10`，`schema.sql` 末尾也设为 10。若目标为其他版本，全部按实际版本一致更新。
- 同步 `README.md` 的车型、皮肤、数据库版本和升级范围；同步 `tests/test_app.py` 的版本断言。

### 5. 验收与上线前检查

- 变更前按项目 `backup.cmd` 备份并保留 `instance/`。
- 分别验证新建库、v9→目标版本、较早版本连续升级；核对 `PRAGMA user_version`、`foreign_key_check`、旧车记录和乘客关系。
- 测试汉两种皮肤的新建、编辑、管理员操作、非法皮肤、缺字段旧表单回退和活动页同步。
- 浏览器验收车型反复切换、保存后重开编辑、错误回显、活动页同步和窄屏缩略效果。
- 本包未执行应用测试、迁移、启动、重启或部署；这些步骤按目标环境权限和当次授权执行。

## 来源与使用说明

- 车型参考：BYD 官方 Han EV 外观图，强调同代 Dragon Face 汉 EV 的轮廓、细长前灯和贯穿镀铬前饰条。原指定中国汉 EV 荣耀版页面在检查时直连返回 404，因此补用了 BYD 官方国际 Han EV 页面及车型图；不承诺精确年份、配置或全部徽标细节。
- 风格参考：项目已有 SU7 与先前制作的 CT5 车辆精灵，主要用于统一视角、透明底和 UI 表现。
- 滴滴版为用户指定的**装饰性概念皮肤**，不是官方车队规格、授权或商业合作声明；无出租车顶灯。
- 品牌、文字和车型标识归各权利人所有。本包是 AI 生成素材；第三方参考照片未再分发。对外商业发布前应自行确认适用的品牌使用许可。

官方车型页：https://www.byd.com/us/car/han-ev
原指定中国车型页：https://www.byd.com/cn/dynasty-home/models/han/han-ev-rongyao
官方外形参考：https://www.byd.com/material/byd-site/us/product/han-ev/img/s9-car-1.png
仓库：https://github.com/IcarusLight/GoTogether

源码核对：
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/store.py
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/templates/travel.html
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/schema.sql
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/migrations/migration_9.sql

制作日期：2026-10-20；白车修订版：v2
