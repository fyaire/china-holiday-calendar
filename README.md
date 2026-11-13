# 中国大陆法定节假日订阅源

维护一份可验证、可发布、可被 Apple 日历等客户端订阅的中国大陆法定节假日与调休日历。

本项目只收录国务院办公厅正式公布的年度放假和调休安排，不预测未公布年份，也不收录二十四节气、传统节日或个人日程。

## 当前覆盖

- 2027 年：国务院办公厅《国务院办公厅关于2027年部分节假日安排的通知》
- 文号：国办发明电〔2026〕10号
- 发布日期：2026-11-05
- 官方来源：https://www.gov.cn/zhengce/content/202611/content_7085101.htm
- 全文核验：https://www3.xinhuanet.com/politics/20261105/69adf4f2f2db490c9fc518874a24d602/c.html

## 目录

```text
data/                       每年的结构化官方数据
dist/china-holidays.ics     可直接发布和订阅的生成结果
scripts/build.py            构建及一致性检查入口
src/china_calendar/         ICS 生成与数据校验逻辑
tests/                      自动化测试
```

## 使用

环境只需要 Python 3，无第三方依赖。

```bash
make build   # 根据 data/*.json 重新生成 ICS
make check   # 检查生成文件是否与数据一致
make test    # 执行测试
```

也可以直接运行：

```bash
python3 scripts/build.py
python3 scripts/build.py --check
python3 -m unittest discover -s tests -v
```

## 每年维护流程

1. 等待国务院办公厅发布下一年度正式通知。
2. 复制上一年的 `data/YYYY.json`，改为新年份并录入所有放假区间和调休上班日。
3. 保存官方通知网址、文号、发布日期和全文核验地址。
4. 运行 `make build && make test && make check`。
5. 人工对照原文复核一次，再发布 `dist/china-holidays.ics`。

不要预先推算未公布年份。国务院正式安排可能与通常规则不同。

## 发布与订阅

本项目的固定 Raw 订阅 URL：

```text
https://raw.githubusercontent.com/fyaire/china-holiday-calendar/main/dist/china-holidays.ics
```

在 Apple 日历中选择“文件 → 新建日历订阅”，粘贴 URL，并把“位置”设为 iCloud。建议将自动刷新设为每天或每周。

直接导入本地 `.ics` 只是复制当前事件，不会自动获得后续更新；要自动更新必须使用可访问的 HTTPS URL 进行订阅。

## 数据约定

- `holidays[].end` 是实际假期最后一天；生成 ICS 时会自动将 `DTEND` 转为下一天，因为 iCalendar 的全天日程结束日期不包含在事件内。
- `workdays[]` 表示因调休而需要上班的周末。
- UID 由年份和数据 ID 稳定生成；发布后不要随意修改已有 ID，否则客户端可能产生重复事件。
- 所有事件为全天、透明状态，不占用忙碌时间。

