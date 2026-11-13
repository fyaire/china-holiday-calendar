# 中国日历订阅源

维护三份相互独立、可验证、可被 Apple 日历等客户端订阅的日历：

1. 中国大陆法定节假日与调休
2. 二十四节气
3. 常用节日

拆分后可以分别开关，也不会把节气、文化节日误认为法定假期。

## 订阅地址

### 法定节假日与调休

```text
https://raw.githubusercontent.com/fyaire/china-holiday-calendar/main/dist/china-holidays.ics
```

只收录国务院办公厅正式公布的放假与调休安排，不预测未公布年份。当前覆盖2027年。

### 二十四节气

```text
https://raw.githubusercontent.com/fyaire/china-holiday-calendar/main/dist/solar-terms.ics
```

当前覆盖2027年，包括清明在内的完整24个节气，不包含任何法定假期或其他节日。

### 常用节日

```text
https://raw.githubusercontent.com/fyaire/china-holiday-calendar/main/dist/common-festivals.ics
```

固定日期和按星期计算的节日覆盖2027—2050年；农历节日当前覆盖2027年。包括情人节、母亲节、父亲节、七夕、重阳、感恩节、平安夜和圣诞节等，不表示法定放假。

在 Apple 日历中选择“文件 → 新建日历订阅”，分别粘贴需要的 URL，把“位置”设为 iCloud，并将自动刷新设为每天或每周。

## 数据来源

### 法定节假日

- 国务院办公厅《国务院办公厅关于2027年部分节假日安排的通知》
- 文号：国办发明电〔2026〕10号
- 官方来源：https://www.gov.cn/zhengce/content/202611/content_7085101.htm
- 全文核验：https://www3.xinhuanet.com/politics/20261105/69adf4f2f2db490c9fc518874a24d602/c.html

### 二十四节气和农历节日

- Apple 中国大陆节假日订阅：https://calendars.icloud.com/holidays/cn_zh.ics/
- 23个非清明节气交叉核验：https://raw.githubusercontent.com/KaitoHH/24-jieqi-ics/master/23_solar_terms_2015-01-01_2050-12-31.ics

节气和农历节日按年度保存经过核验的日期，不依赖运行时网络接口。

## 目录

```text
data/holidays/                  法定假期与调休年度数据
data/solar-terms/               二十四节气年度数据
data/common-festivals.json      固定日期和星期规则
data/common-festivals/          农历节日年度数据
dist/china-holidays.ics         法定假期订阅源
dist/solar-terms.ics            二十四节气订阅源
dist/common-festivals.ics       常用节日订阅源
scripts/build.py                构建及一致性检查入口
src/china_calendar/             ICS 生成与数据校验逻辑
tests/                          自动化测试
```

## 构建和测试

环境只需要 Python 3，无第三方依赖。

```bash
make build
make test
make check
```

也可以直接运行：

```bash
python3 scripts/build.py
python3 -m unittest discover -s tests -v
python3 scripts/build.py --check
```

## 年度维护

1. 国务院发布正式通知后，新增 `data/holidays/YYYY.json`。
2. 核验下一年度24个节气后，新增 `data/solar-terms/YYYY.json`。
3. 核验元宵、七夕、重阳等农历节日后，新增 `data/common-festivals/YYYY.json`。
4. 运行 `make build && make test && make check`。
5. 人工对照来源复核，再提交并推送。

不要预先推算法定放假安排。国务院正式安排可能与通常规则不同。

## 数据约定

- `holidays[].end` 是实际假期最后一天；生成 ICS 时自动把 `DTEND` 转为下一天，因为 iCalendar 的全天日程结束日期不包含在事件内。
- `workdays[]` 表示因调休而需要上班的周末。
- 固定日期和星期规则可提前生成；农历节日和节气使用按年核验的数据。
- UID 由年份、数据 ID 和日历类别稳定生成；发布后不要随意修改已有 ID。
- 所有事件均为全天、透明状态，不占用忙碌时间。
