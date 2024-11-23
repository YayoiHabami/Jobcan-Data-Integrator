# データベースのテーブル情報

　本項では、本アプリケーションが使用するデータベースのテーブルについて説明します。

> [全体の目次に戻る](../README.html)

## 目次

- [目次](#目次)
- [概要](#概要)
- [ユーザー情報 (users)](#ユーザー情報-users)
- [グループ (groups)](#グループ-groups)
- [役職 (positions)](#役職-positions)
- [プロジェクト (projects)](#プロジェクト-projects)
- [取引先 (company)](#取引先-company)
- [確定済み未出力仕訳 (fix\_journals)](#確定済み未出力仕訳-fix_journals)
- [フォーム (forms)](#フォーム-forms)
- [申請書 (requests)](#申請書-requests)
  - [メイン (requests)](#メイン-requests)
  - [customized\_items](#customized_items)
  - [expense](#expense)
  - [payment](#payment)
  - [ec](#ec)
  - [approval\_process](#approval_process)
  - [viewers](#viewers)
  - [変更履歴 (modify\_logs)](#変更履歴-modify_logs)
  - [ファイル (files)](#ファイル-files)
  - [申請書 (requests) まとめ](#申請書-requests-まとめ)


## 概要

　ジョブカンAPIで取得できるデータのうち、本アプリケーションで取得しているデータとテーブルとの対応関係を以下に示します。テーブル名のうち、左に🔵が付与されているものは最上位のテーブルとなります。

**表** ジョブカンAPIとテーブルの対応関係

| ジョブカンAPI | テーブル |
| --- | --- |
| ユーザー情報 | 🔵`users`<br>`user_groups`<br>`user_positions`<br>`user_bank_accounts` |
| グループ | 🔵`groups` |
| 役職 | 🔵`positions` |
| 申請書 | 🔵`requests`<br>`customized_items`<br>`generic_masters`<br>`generic_master_additional_items`<br>`table_data`<br>`expense`<br>`expense_specifics`<br>`expense_specific_rows`<br>`custom_items`<br>`custom_item_values`<br>`custom_item_value_extension_items`<br>`payment`<br>`payment_specifics`<br>`payment_specific_rows`<br>`ec`<br>`shipping_address`<br>`ec_specifics`<br>`ec_specific_rows`<br>`approval_process`<br>`approval_route_modify_logs`<br>`approval_steps`<br>`approvers`<br>`comments`<br>`comment_associations`<br>`viewers`<br>`modify_logs`<br>`modify_log_details`<br>`modify_log_detail_specifics`<br>`files`<br>`file_associations` |

## ユーザー情報 (users)

　ジョブカンに登録されているユーザー情報を格納するテーブルです。ユーザー情報には、ユーザーの基本情報と、ユーザーが所属するグループや役職、銀行口座情報が含まれます。

```mermaid
erDiagram
    users ||--o{ user_groups : ""
    users ||--o{ user_positions : ""
    users ||--o| user_bank_accounts : ""

    groups ||--o{ user_groups : ""
    groups ||--o{ user_positions : ""
    positions ||--o{ user_positions : ""

users {
    INTEGER id PK "管理用"
    TEXT user_code
    TEXT email
    TEXT last_name
    TEXT first_name
    INTEGER is_approver
    INTEGER user_role
    TEXT memo
}

user_groups {
    INTEGER id PK "管理用"
    INTEGER user_id FK "user.id"
    TEXT group_code FK "groups.group_code"
}

user_positions {
    INTEGER id PK "管理用"
    INTEGER user_id FK "user.id"
    TEXT position_code FK "positions.position_code"
    TEXT group_code FK "groups.group_code"
}

user_bank_accounts {
    INTEGER user_id PK "user.id"
    TEXT bank_code
    TEXT bank_name
    TEXT bank_name_kana
    TEXT branch_code
    TEXT branch_name
    TEXT branch_name_kana
    TEXT bank_account_type_code
    TEXT bank_account_code
    TEXT bank_account_name_kana
}
```

**図** ユーザー情報テーブルのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

## グループ (groups)

　ジョブカンに登録されているグループ情報を格納するテーブルです。グループ情報には、グループの基本情報と、グループに所属するユーザー情報が含まれます。

```mermaid
erDiagram
    groups ||--o{ user_groups : ""
    groups ||--o{ user_positions : ""

groups {
    TEXT group_code PK
    TEXT group_name
    TEXT parent_group_code
    TEXT description
}
```

**図** グループテーブルのER図．`user_groups`と`user_positions`は[ユーザー情報](#ユーザー情報-users)のテーブルとの関連を示しています

## 役職 (positions)

　ジョブカンに登録されている役職情報を格納するテーブルです。役職情報には、役職の基本情報が含まれます。

```mermaid
erDiagram
    positions ||--o{ user_positions : ""

positions {
    TEXT position_code PK
    TEXT position_name
    TEXT description
}
```

**図** 役職テーブルのER図．`user_positions`は[ユーザー情報](#ユーザー情報-users)のテーブルとの関連を示しています

## プロジェクト (projects)

　ジョブカンに登録されているプロジェクト情報を格納するテーブルです。プロジェクト情報には、プロジェクトの基本情報が含まれます。

```mermaid
erDiagram
    projects

projects {
    TEXT project_code PK
    TEXT project_name
}
```

**図** プロジェクトテーブルのER図．

## 取引先 (company)

　ジョブカンに登録されている取引先情報を格納するテーブルです。取引先情報には、取引先の基本情報が含まれます。

　ここで、`bank_account_type_code`は`"1"`などの数字で表されていますが、確認できる範囲では以下のように対応しているようです。

- `"1"`: 普通
- `"2"`: 当座
- `"9"`: その他

```mermaid

erDiagram
    company

company {
    TEXT company_code PK
    TEXT company_name
    TEXT zip_code
    TEXT address
    TEXT bank_code
    TEXT bank_name
    TEXT branch_code
    TEXT branch_name
    TEXT bank_account_type_code
    TEXT bank_account_code
    TEXT bank_account_name_kana
    TEXT invoice_registrated_number
}
```

**図** 取引先テーブルのER図．

## 確定済み未出力仕訳 (fix_journals)

　ジョブカンに登録されている確定済み未出力仕訳情報を格納するテーブルです。APIによるデータ取得時点で未出力の仕訳情報が格納されますが、本ソフトウェアが当テーブルからデータを削除することはありません。このため、古いデータについては出力済みの可能性があります。

```mermaid
erDiagram
    fix_journals ||--o{ custom_journal_items : ""

fix_journals {
    INTEGER journal_id PK
    TEXT journal_type
    TEXT journal_date
    TEXT req_date
    TEXT journal_summary
    TEXT view_id
    INTEGER specifics_row_number
    TEXT company_code
    TEXT company_name
    TEXT user_code
    TEXT user_name
    TEXT debit_account_title_code
    TEXT debit_account_title_name
    TEXT debit_account_sub_title_code
    TEXT debit_account_sub_title_name
    TEXT debit_tax_category_code
    TEXT debit_tax_category_name
    INTEGER debit_amount
    INTEGER debit_tax_amount
    INTEGER debit_amount_without_tax
    TEXT debit_group_code
    TEXT debit_group_name
    TEXT debit_accounting_group_code
    TEXT debit_project_code
    TEXT debit_project_name
    TEXT credit_account_title_code
    TEXT credit_account_title_name
    TEXT credit_account_sub_title_code
    TEXT credit_account_sub_title_name
    TEXT credit_tax_category_code
    TEXT credit_tax_category_name
    INTEGER credit_amount
    INTEGER credit_tax_amount
    INTEGER credit_amount_without_tax
    TEXT credit_group_code
    TEXT credit_group_name
    TEXT credit_accounting_group_code
    TEXT credit_project_code
    TEXT credit_project_name
    TEXT invoice_registrated_number
}

custom_journal_items {
    INTEGER journal_id FK
    TEXT key
    TEXT value
    TEXT generic_master_record_code
}
```

**図** 確定済み未出力仕訳テーブルのER図．

## フォーム (forms)

　ジョブカンに登録されているフォーム情報を格納するテーブルです。フォーム情報には、フォームの基本情報が含まれます。

```mermaid
erDiagram
forms {
    INTEGER id PK
    TEXT category
    TEXT form_type
    TEXT settlement_type
    TEXT name
    TEXT view_type
    TEXT description
}
```

**図** フォームテーブルのER図．

## 申請書 (requests)

　ジョブカンに登録されている申請書情報を格納するテーブルです。申請書情報には、申請書の基本情報と、申請書に関連する情報が含まれます。

### メイン (requests)

　申請書の基本情報を格納するテーブルです。申請書の基本情報には、申請書のタイトルやステータス、申請書の種類や申請書の提出日時、申請者の情報などが含まれます。

```mermaid
erDiagram
    requests ||--o{ customized_items : ""
    requests ||--o| expense : ""
    requests ||--o| payment : ""
    requests ||--o| ec : ""
    requests ||--o| approval_process : ""
    requests ||--o{ viewers : ""
    requests ||--o{ modify_logs : ""
    requests ||--o{ file_associations : ""

requests{
    TEXT id PK
    TEXT title
    TEXT status
    INTEGER form_id
    TEXT form_name
    TEXT form_type
    TEXT settlement_type
    DATETIME applied_date
    TEXT applicant_code
    TEXT applicant_last_name
    TEXT applicant_first_name
    TEXT applicant_group_name
    TEXT applicant_group_code
    TEXT applicant_position_name
    TEXT proxy_applicant_last_name
    TEXT proxy_applicant_first_name
    TEXT group_name
    TEXT group_code
    TEXT project_name
    TEXT project_code
    TEXT flow_step_name
    BOOLEAN is_content_changed
    INTEGER total_amount
    DATETIME pay_at
    DATETIME final_approval_period
    DATETIME final_approved_date
}

```

**図** 申請書テーブルのER図(一部)．`requests`テーブルと直接の関連があるテーブルのみを示しています

### customized_items

```mermaid
erDiagram
    requests ||--o{ customized_items : ""

    customized_items ||--o| generic_masters : ""
    customized_items ||--o{ file_associations : ""
    customized_items ||--o{ table_data : ""

    generic_masters ||--o{ generic_master_additional_items : ""

    table_data ||--o{ generic_masters : ""

customized_items {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    TEXT title
    TEXT content
    INTEGER item_index "管理用・JSON/DB上でのアイテム番号"
}

table_data {
    INTEGER id PK "管理用"
    INTEGER customized_item_id FK "customized_items.id"
    INTEGER column_number
    TEXT value
    INTEGER index_1 "管理用・JSON/DB上での列番号 (二重リストの外側)"
    INTEGER index_2 "管理用・JSON/DB上での行番号 (二重リストの内側)"
}

generic_masters {
    INTEGER id PK "管理用"
    TEXT record_name
    TEXT record_code
    INTEGER customized_item_id FK "customized_items.id"
    INTEGER table_data_id FK "table_data.id"
}

generic_master_additional_items {
    INTEGER id PK "管理用"
    INTEGER generic_master_id FK "generic_masters.id"
    TEXT item_value
    INTEGER item_index "管理用・JSON/DB上でのアイテム番号"
}
```

**図** customized_itemsテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### expense

```mermaid
erDiagram
    requests ||--o| expense : ""

    expense ||--o{ expense_specifics : ""
    expense_specifics ||--o{ expense_specific_rows : ""
    expense_specific_rows ||--o{ custom_items : ""
    expense_specific_rows ||--o{ file_associations : ""
    custom_items ||--o| custom_item_values : ""
    custom_item_values ||--o{ custom_item_value_extension_items : ""

expense {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    INTEGER amount
    TEXT related_request_title
    TEXT related_request_id
    BOOLEAN use_suspense_payment
    TEXT content_description
    INTEGER advanced_payment
    INTEGER suspense_payment_amount
}

expense_specifics {
    INTEGER id PK "管理用"
    INTEGER expense_id FK "expense.id"
    TEXT type
    INTEGER col_number "管理用・JSON/DB上での列番号"
}

expense_specific_rows {
    INTEGER id PK "管理用"
    INTEGER expense_specific_id FK "expense_specifics.id"
    TEXT row_number
    DATE use_date
    TEXT group_name
    TEXT project_name
    TEXT content_description
    TEXT breakdown
    INTEGER amount
}

custom_items {
    INTEGER id PK "管理用"
    INTEGER expense_specific_row_id FK "expense_specific_rows.id"
    TEXT name
    TEXT item_type
    TEXT value "NULLの場合、値はcustom_item_valuesに格納される"
    INTEGER item_index "管理用・JSON/DB上でのアイテム番号"
}

custom_item_values {
    INTEGER id PK "管理用"
    INTEGER custom_item_id FK "custom_items.id"
    TEXT generic_master_code
    TEXT generic_master_record_name
    TEXT generic_master_record_code
    TEXT content
    TEXT memo
}

custom_item_value_extension_items {
    INTEGER id PK "管理用"
    INTEGER custom_item_value_id FK "custom_item_values.id"
    TEXT name
    TEXT value
    INTEGER item_index "管理用・JSON/DB上でのアイテム番号"
}
```

**図** expenseテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### payment

```mermaid
erDiagram
    requests ||--o| payment : ""

    payment ||--o{ payment_specifics : ""
    payment_specifics ||--o{ payment_specific_rows : ""
    payment_specific_rows ||--o{ file_associations : ""

payment {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    INTEGER amount
    TEXT related_request_title
    TEXT related_request_id
    TEXT content_description
}

payment_specifics {
    INTEGER id PK "管理用"
    INTEGER payment_id FK "payment.id"
    TEXT type
    INTEGER col_number "管理用・JSON/DB上での列番号"
}

payment_specific_rows {
    INTEGER id PK "管理用"
    INTEGER payment_specific_id FK "payment_specifics.id"
    TEXT company_name
    TEXT zip_code
    TEXT address
    TEXT bank_name
    TEXT bank_name_kana
    TEXT bank_account_name_kana
    INTEGER bank_code
    INTEGER branch_code
    TEXT row_number
    DATE use_date
    TEXT group_name
    TEXT project_name
    TEXT content_description
    TEXT breakdown
    INTEGER amount
}
```

**図** paymentテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### ec

```mermaid
erDiagram
    requests ||--o| ec : ""

    ec ||--o| shipping_address : ""
    ec ||--o{ ec_specifics : ""
    ec_specifics ||--o{ ec_specific_rows : ""

ec {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    TEXT related_request_id
    TEXT related_request_title
    TEXT content_description
    TEXT billing_destination
    INTEGER shipping_address_id FK "shipping_address.id"
}

shipping_address {
    INTEGER id PK "管理用"
    INTEGER ec_id FK "ec.id"
    TEXT shipping_address_name
    TEXT zip_code
    TEXT country
    TEXT state
    TEXT city
    TEXT address1
    TEXT address2
    TEXT company_name
    TEXT contact_name
    TEXT tel
    TEXT email
}

ec_specifics {
    INTEGER id PK "管理用"
    INTEGER ec_id FK "ec.id"
    TEXT order_id
    DATETIME retention_deadline
    INTEGER tax_amount
    INTEGER shipping_amount
    INTEGER total_price
    INTEGER total_amount
}

ec_specific_rows {
    INTEGER id PK "管理用"
    INTEGER ec_specific_id FK "ec_specifics.id"
    INTEGER row_number
    TEXT item_name
    TEXT item_url
    TEXT item_id
    TEXT manufacturer_name
    TEXT sold_by
    TEXT fulfilled_by
    INTEGER unit_price
    TEXT quantity
    INTEGER subtotal
}
```

**図** ecテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### approval_process

```mermaid
erDiagram
    requests ||--o| approval_process : ""

    approval_process ||--o{ approval_route_modify_logs : ""
    approval_process ||--o{ approval_steps : ""
    approval_steps ||--o{ approvers : ""
    approval_steps ||--o{ comment_associations : ""
    approval_steps ||--o{ file_associations : ""
    approval_process ||--o{ comment_associations : ""
    approval_process ||--o{ file_associations : ""

    comments ||--o{ comment_associations : ""

approval_process {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    BOOLEAN is_route_changed_by_applicant
}

approval_route_modify_logs {
    INTEGER id PK "管理用"
    INTEGER approval_process_id FK "approval_process.id"
    DATETIME date
    TEXT user_name
    INTEGER log_index "管理用・JSON/DB上でのログ番号"
}

approval_steps {
    INTEGER id PK "管理用"
    INTEGER approval_process_id FK "approval_process.id"
    TEXT name
    TEXT condition
    TEXT status
    INTEGER step_index "管理用・JSON/DB上でのステップ番号"
}

approvers {
    INTEGER id PK "管理用"
    INTEGER approval_step_id FK "approval_steps.id"
    TEXT status
    DATETIME approved_date
    TEXT approver_name
    TEXT approver_code
    TEXT proxy_approver_name
    TEXT proxy_approver_code
    INTEGER approver_index "管理用・JSON/DB上でのapprover番号"
}

comments {
    INTEGER id PK "管理用"
    TEXT user_name
    DATETIME date
    TEXT text
    BOOLEAN deleted
}

comment_associations {
    INTEGER id PK "管理用"
    INTEGER comment_id FK "comments.id"
    INTEGER approval_step_id FK "approval_steps.id"
    INTEGER approval_after_completion_id FK "approval_process.id"
}
```

**図** approval_processテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### viewers

```mermaid
erDiagram
    requests ||--o{ viewers : ""

viewers {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    TEXT user_name
    TEXT status
    TEXT group_name
    TEXT position
    INTEGER viewer_index "管理用・JSON/DB上でのビュー番号"
}
```

**図** viewersテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### 変更履歴 (modify_logs)

　申請書の変更履歴を格納するテーブルです。変更履歴には、その変更が行われた日時やユーザー名、変更内容が含まれます。

```mermaid
erDiagram
    requests ||--o{ modify_logs : ""

    modify_logs ||--o{ modify_log_details : ""
    modify_log_details ||--o{ modify_log_detail_specifics : ""

modify_logs {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    DATETIME date
    TEXT user_name
    INTEGER log_index "管理用・JSON/DB上でのログ番号"
}

modify_log_details {
    INTEGER id PK "管理用"
    INTEGER modify_log_id FK "modify_logs.id"
    TEXT title
    TEXT old_value
    TEXT new_value
    TEXT log_type
    INTEGER log_detail_index "管理用・JSON/DB上での番号"
}

modify_log_detail_specifics {
    INTEGER id PK "管理用"
    INTEGER modify_log_detail_id FK "modify_log_details.id"
    TEXT status
    TEXT difference
    INTEGER specific_index "管理用・JSON/DB上でのステップ番号"
}
```

**図** modify_logsテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### ファイル (files)

　申請書に添付されたファイル情報を格納するテーブルです。ファイル情報には、ファイルの基本情報およびどこに紐づいているかが含まれます。

```mermaid
erDiagram
    requests ||--o{ file_associations : ""
    customized_items ||--o{ file_associations : ""
    expense_specific_rows ||--o{ file_associations : ""
    payment_specific_rows ||--o{ file_associations : ""
    approval_steps ||--o{ file_associations : ""
    approval_process ||--o{ file_associations : ""
    files ||--o{ file_associations : ""

files {
    TEXT id PK
    TEXT name
    TEXT type
    TEXT user_name
    DATETIME date
    BOOLEAN deleted
}

file_associations {
    INTEGER id PK "管理用"
    TEXT request_id FK "requests.id"
    TEXT file_id FK "files.id"
    INTEGER customized_item_id FK "customized_items.id"
    INTEGER expense_specific_row_id FK "expense_specific_rows.id"
    INTEGER payment_specific_row_id FK "payment_specific_rows.id"
    INTEGER approval_step_id FK "approval_steps.id"
    INTEGER approval_after_completion_id FK "approval_process.id"
    INTEGER default_attachment "request_id に何回 default_attachment として登録されるか"
}
```

**図** filesテーブルまわりのER図．`管理用`と書かれている部分は元データには存在しないキーです．また、複合UNIQUE制約については省略しています．

### 申請書 (requests) まとめ

作成したテーブルのER図を以下に作成します。

```mermaid
erDiagram
    requests ||--o{ customized_items : ""
    requests ||--o| expense : ""
    requests ||--o| payment : ""
    requests ||--o| ec : ""
    requests ||--o| approval_process : ""
    requests ||--o{ viewers : ""
    requests ||--o{ modify_logs : ""
    requests ||--o{ file_associations : ""

    customized_items ||--o| generic_masters : ""
    customized_items ||--o{ file_associations : ""
    customized_items ||--o{ table_data : ""
    table_data ||--o{ generic_masters : ""
    generic_masters ||--o{ generic_master_additional_items : ""

    expense ||--o{ expense_specifics : ""
    expense_specifics ||--o{ expense_specific_rows : ""
    expense_specific_rows ||--o{ custom_items : ""
    expense_specific_rows ||--o{ file_associations : ""
    custom_items ||--o| custom_item_values : ""
    custom_item_values ||--o{ custom_item_value_extension_items : ""

    payment ||--o{ payment_specifics : ""
    payment_specifics ||--o{ payment_specific_rows : ""
    payment_specific_rows ||--o{ file_associations : ""

    ec ||--o| shipping_address : ""
    ec ||--o| ec_specifics : ""
    ec_specifics ||--o{ ec_specific_rows : ""

    approval_process ||--o{ approval_route_modify_logs : ""
    approval_process ||--o{ approval_steps : ""
    approval_steps ||--o{ approvers : ""
    approval_steps ||--o{ comment_associations : ""
    approval_steps ||--o{ file_associations : ""
    approval_process ||--o{ comment_associations : ""
    approval_process ||--o{ file_associations : ""

    modify_logs ||--o{ modify_log_details : ""
    modify_log_details ||--o{ modify_log_detail_specifics : ""

    files ||--o{ file_associations : ""
    comments ||--o{ comment_associations : ""

requests {
    TEXT id
    TEXT title
    TEXT status
    INTEGER form_id
    TEXT form_name
    TEXT form_type
    TEXT settlement_type
    DATETIME applied_date
    TEXT applicant_code
    TEXT applicant_last_name
    TEXT applicant_first_name
    TEXT applicant_group_name
    TEXT applicant_group_code
    TEXT applicant_position_name
    TEXT proxy_applicant_last_name
    TEXT proxy_applicant_first_name
    TEXT group_name
    TEXT group_code
    TEXT project_name
    TEXT project_code
    TEXT flow_step_name
    BOOLEAN is_content_changed
    INTEGER total_amount
    DATETIME pay_at
    DATETIME final_approval_period
    DATETIME final_approved_date
}

customized_items {
    INTEGER id
    TEXT request_id
    TEXT title
    TEXT content
    INTEGER item_index "JSON/DB上でのアイテム番号"
}

generic_masters {
    INTEGER id
    TEXT record_name
    TEXT record_code
    INTEGER customized_item_id
    INTEGER table_data_id
}

generic_master_additional_items {
    INTEGER id
    INTEGER generic_master_id
    TEXT item_value
    INTEGER item_index "JSON/DB上でのアイテム番号"
}

table_data {
    INTEGER id
    INTEGER customized_item_id
    INTEGER column_number
    TEXT value
    INTEGER index_1 "JSON/DB上での列番号 (二重リストの外側)"
    INTEGER index_2 "JSON/DB上での行番号 (二重リストの内側)"
}

expense {
    INTEGER id
    TEXT request_id
    INTEGER amount
    TEXT related_request_title
    TEXT related_request_id
    BOOLEAN use_suspense_payment
    TEXT content_description
    INTEGER advanced_payment
    INTEGER suspense_payment_amount
}

expense_specifics {
    INTEGER id
    INTEGER expense_id
    TEXT type
    INTEGER col_number "JSON/DB上での列番号"
}

expense_specific_rows {
    INTEGER id
    INTEGER expense_specific_id
    TEXT row_number
    DATE use_date
    TEXT group_name
    TEXT project_name
    TEXT content_description
    TEXT breakdown
    INTEGER amount
}

custom_items {
    INTEGER id
    INTEGER expense_specific_row_id
    TEXT name
    TEXT item_type
    TEXT value "NULLの場合、値はcustom_item_valuesに格納される"
    INTEGER item_index "JSON/DB上でのアイテム番号"
}

custom_item_values {
    INTEGER id
    INTEGER custom_item_id
    TEXT generic_master_code
    TEXT generic_master_record_name
    TEXT generic_master_record_code
    TEXT content
    TEXT memo
}

custom_item_value_extension_items {
    INTEGER id
    INTEGER custom_item_value_id
    TEXT name
    TEXT value
    INTEGER item_index "JSON/DB上でのアイテム番号"
}

payment {
    INTEGER id
    TEXT request_id
    INTEGER amount
    TEXT related_request_title
    TEXT related_request_id
    TEXT content_description
}

payment_specifics {
    INTEGER id
    INTEGER payment_id
    TEXT type
    INTEGER col_number "JSON/DB上での列番号"
}

payment_specific_rows {
    INTEGER id
    INTEGER payment_specific_id
    TEXT company_name
    TEXT zip_code
    TEXT address
    TEXT bank_name
    TEXT bank_name_kana
    TEXT bank_account_name_kana
    INTEGER bank_code
    INTEGER branch_code
    TEXT row_number
    DATE use_date
    TEXT group_name
    TEXT project_name
    TEXT content_description
    TEXT breakdown
    INTEGER amount
}

ec {
    INTEGER id
    TEXT request_id
    TEXT related_request_id
    TEXT related_request_title
    TEXT content_description
    TEXT billing_destination
    INTEGER shipping_address_id
}

shipping_address {
    INTEGER id
    INTEGER ec_id
    TEXT shipping_address_name
    TEXT zip_code
    TEXT country
    TEXT state
    TEXT city
    TEXT address1
    TEXT address2
    TEXT company_name
    TEXT contact_name
    TEXT tel
    TEXT email
}

ec_specifics {
    INTEGER id
    INTEGER ec_id
    TEXT order_id
    DATETIME retention_deadline
    INTEGER tax_amount
    INTEGER shipping_amount
    INTEGER total_price
    INTEGER total_amount
}

ec_specific_rows {
    INTEGER id
    INTEGER ec_specific_id
    INTEGER row_number
    TEXT item_name
    TEXT item_url
    TEXT item_id
    TEXT manufacturer_name
    TEXT sold_by
    TEXT fulfilled_by
    INTEGER unit_price
    TEXT quantity
    INTEGER subtotal
}

approval_process {
    INTEGER id
    TEXT request_id
    BOOLEAN is_route_changed_by_applicant
}

approval_route_modify_logs {
    INTEGER id
    INTEGER approval_process_id
    DATETIME date
    TEXT user_name
    INTEGER log_index "JSON/DB上でのログ番号"
}

approval_steps {
    INTEGER id
    INTEGER approval_process_id
    TEXT name
    TEXT condition
    TEXT status
    INTEGER step_index "JSON/DB上でのステップ番号"
}

approvers {
    INTEGER id
    INTEGER approval_step_id
    TEXT status
    DATETIME approved_date
    TEXT approver_name
    TEXT approver_code
    TEXT proxy_approver_name
    TEXT proxy_approver_code
    INTEGER approval_index "JSON/DB上でのapprover番号"
}

comments {
    INTEGER id
    TEXT user_name
    DATETIME date
    TEXT text
    BOOLEAN deleted
}

comment_associations {
    INTEGER id
    INTEGER comment_id
    INTEGER approval_step_id
    INTEGER approval_after_completion_id "approval_process.id"
}

viewers {
    INTEGER id
    TEXT request_id
    TEXT user_name
    TEXT status
    TEXT group_name
    TEXT position
    INTEGER view_index "JSON/DB上でのビュー番号"
}

modify_logs {
    INTEGER id
    TEXT request_id
    DATETIME date
    TEXT user_name
    INTEGER log_index "JSON/DB上でのログ番号"
}

modify_log_details {
    INTEGER id
    INTEGER modify_log_id
    TEXT title
    TEXT old_value
    TEXT new_value
    TEXT log_type
    INTEGER log_detail_index "JSON/DB上での番号"
}

modify_log_detail_specifics {
    INTEGER id
    INTEGER modify_log_detail_id
    TEXT status
    TEXT difference
    INTEGER specific_index "JSON/DB上でのステップ番号"
}

files {
    TEXT id
    TEXT name
    TEXT type
    TEXT user_name
    DATETIME date
    BOOLEAN deleted
}

file_associations {
    INTEGER id
    TEXT request_id
    TEXT file_id
    INTEGER customized_item_id
    INTEGER expense_specific_row_id
    INTEGER payment_specific_row_id
    INTEGER approval_step_id
    INTEGER approval_after_completion_id "approval_process.id"
    INTEGER default_attachment "request_id に何回 default_attachment として登録されるか"
}
```

---

> [全体の目次に戻る](../README.html)
