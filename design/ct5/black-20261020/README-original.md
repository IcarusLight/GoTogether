# 黑色凯迪拉克 CT5 · 素材包（接入说明修订版）

核对基线：GoTogether 提交 `4b6762b1f91f13a5260935cdd10fd0ff762b4a03`，2026-10-20。
本包沿用已交付图片，不重新生成；修正资源目录、车辆 ID 和数据库接入步骤。此前扁平路径与仅修改车型列表的说明已被本版替代。

## 已按项目相对路径打包

- `static/vehicles/ct5/default.webp`：网页主图，640 × 440，真实 Alpha，质量 88，49,046 字节。
- `design/ct5-black-20261020/generated.png`：1620 × 971 原始透明生成图。
- `design/ct5-black-20261020/default.png`：640 × 440 透明 PNG 导出。
- `design/ct5-black-20261020/prompt.txt`：原始生成提示。
- `design/ct5-black-20261020/sources.json`：来源、参数、校验值和相对路径记录。

解压后可将 `static/`、`design/` 中的新增目录合并到项目对应位置，不要用整个目录覆盖现有资源。
使用车辆 ID `ct5`，默认外观 ID `default`。`blackCT5` 只作为这份素材的描述名称，不再作为数据库车辆 ID。

## 接入检查清单（尚未实施）

1. **复制资源并登记车型**
   - 把上述目录合并到项目。
   - 在 `store.py` 的 `VEHICLE_APPEARANCES` 增加 `'ct5': '凯迪拉克 CT5 · 黑色'`。
   - 当前仅有默认黑色，不必增加 `VEHICLE_COLORS` 条目，也不需要色卡。现有 `vehicle_image()` 会生成 `vehicles/ct5/default.webp`，无需路径特判或修改默认车型 `su7`。

2. **更新新数据库结构**
   - 在 `schema.sql` 的 `vehicles.appearance` 字段 `CHECK (appearance IN (...))` 枚举中追加 `'ct5'`，保留其他车型和原默认值。
   - 该基线当前为 v9；如果没有其他待合并迁移，将文件末尾 `PRAGMA user_version = 9` 升为 `10`。

3. **增加已有数据库的迁移，不能省略**
   - 新增 `migrations/migration_10.sql`，不要改写已执行的 `migration_9.sql` 或更早迁移。
   - 可沿用现有第 8、9 次迁移的方式：新增带完整 11 种车型 CHECK（原 10 种加 `ct5`）的 `appearance_v10` 临时列；把原 `appearance` 值复制进去；删除旧列；将新列重命名为 `appearance`；最后设 `PRAGMA user_version = 10`。
   - 保留车辆 ID、活动、乘客关联、原有车型及颜色值。不能通过删除数据库、重建空库或只改新建库的 `schema.sql` 代替迁移。

4. **同步迁移入口和升级文档**
   - `store.py` 的 `initialize()`：旧版本分支需覆盖 **1–9**（当前只到 8）；迁移目标范围从 `range(version + 1, 10)` 改为 `range(version + 1, 11)`；最终版本校验从 `version != 9` 改为 `version != 10`。
   - 保留现有事务封装和 SQLite ≥ 3.35 的版本检查。
   - 更新根目录 `README.md` 的数据库版本、迁移范围与升级说明；在 `design/README.md` 主图表中登记 `ct5/default.webp` 和本批次来源。
   - 若接入时主分支已经出现其他 v10 迁移，应重新核对最新版本并使用下一个版本号，不覆盖或复用已有迁移。

5. **验证后再上线**
   - 升级前按项目现有 `backup.cmd` 流程备份，保留 `instance/`。
   - 在临时数据库中核对：新建库；v9 升级；较早版本连续升级；CT5 新增和修改保存成功；原车辆/乘客关系不变；`PRAGMA foreign_key_check` 无错误；最终 `user_version` 正确。
   - 同步 `tests/test_app.py` 中受版本号和车辆枚举影响的断言，补上 CT5 保存与迁移覆盖。
   - 核对车型选择、预览、保存后活动页、手机端显示和主图 URL；图片已检查浅/深色背景与 180px 缩略效果。
   - 测试执行、启动和重启遵守项目 `AGENTS.md` 及当次授权。本包没有执行应用、测试、迁移或部署。

**复制图片与增加 `VEHICLE_APPEARANCES` 只完成资源和界面登记；若不更新 CHECK、旧库迁移和版本入口，保存 CT5 仍可能失败。**

## 已核对的源码依据

- [资源规范与接入步骤](https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/design/README.md)
- [当前车型、URL 映射及 initialize()](https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/store.py)
- [新建库 CHECK 与 v9 版本](https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/schema.sql)
- [现有 v9 枚举扩展迁移](https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/migrations/migration_9.sql)
- [备份与升级说明](https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/README.md)

## 图像说明

使用内置图像生成制作，随后保留 Alpha 做透明边裁切、等比缩放、补齐画布与格式导出。车型参考改款 CT5；视角与风格参考项目留存的旧版 SU7 精灵（现路径 `design/vehicle-study-20261014/su7-legacy.webp`）。

这是写实 2.5D 风格的二维图片，不是可旋转的 3D 模型或工程复刻。细节可能与具体年份/配置不同。参考照片未再分发；品牌与车型标识归各自权利人所有，不代表官方授权。

本次仅更新交付包与说明，未改动仓库或数据库。
