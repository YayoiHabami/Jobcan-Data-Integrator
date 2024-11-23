# APIのレスポンスとCSVの対応関係

### 注意点

- 改行の扱い（おそらくそのまま）
- detail/customized_items について、おそらく"title"にHTMLタグが使用されているものについては、CSVに出力されないのだと思われる

### requests と csv の対応表

**表1**. CSVのカラム名とレスポンスのキーの対応表．「そのまま」と書いていないものについては，その後に変換方法を記載．「?」は不明なもの．

| カラム名 | キー | 変換方法 |
| --- | --- | --- |
| 申請ID | id | そのまま |
| 申請ステータス | status | {"completed": "完了", "in_progress": "進行中", "rejected": "却下"?, "canceled": "取り消し"?, "returned": "差し戻し"?, "canceled_after_completion": "完了後取り消し"?} |
| 最終承認日 | final_approved_date | "YYYY/M/D H:M:S" |
| 承認者 | applicant_last_name, applicant_first_name, final_approved_date | 例: "田中 太郎（承認日時：YYYY/MM/DD HH:MM:SS）" |
| フォーム名 | form_name | そのまま |
| タイトル | title | そのまま |
| 申請者メールアドレス | applicant_code -> users/user_code: email | そのまま |
| 申請者コード | user_code | str(user_code) |
| 申請者名（姓） | applicant_last_name | そのまま |
| 申請者名（名） | applicant_first_name | そのまま |
| 申請日時 | applied_date | "YYYY/M/D H:M:S" |
| 関連プロジェクト名 | project_name? | そのまま? |
| 関連グループ名 | applicant_group_name | そのまま |
| コメント | detail/approval_process/after_completion/comments/[user_name, date, text] | "user_name：（YYYY/MM/DD HH:MM:SS）, user_name：text（YYYY/MM/DD HH:MM:SS）" <br> 二つ目の日時がdateのほう、一つ目の日時はafter_completion/filesのdateか、同じユーザのafter_completionの最も早いものか |

### 各CSVの対応

#### 書式 3-3 (form_id = 54142953)

> 第一正規化の行われていない形式で出力される．各行は先頭行に コメント までが記載され、続いてその次の行から 明細の名前 以降が detail/expense/specifics/rows の各要素ごとに記載される．

申請ID, 申請ステータス, 最終承認日, 承認者, フォーム名, タイトル, 申請者メールアドレス, 申請者コード, 申請者名（姓）, 申請者名（名）, 申請日時, 関連グループ名, 関連プロジェクト名

| カラム名 | キー | 変換方法 |
| --- | --- | --- |
| 経費の内訳 | detail/expense/specifics/rows の breakdown? | そのまま (全てが一致していれば) |
| 利用日 | detail/expense/specifics/rows の use_date? | "YYYY/M/D" (最も早いもの) |
| 金額 | total_amount | そのまま |
| 内容 | ? | ? |
| 支払先名 | ? | ? |
| 支払先登録番号 | ? | ? |
| 支払方法 | ? | "立替払い" のみ? |
| 事前申請タイトル | ? | ? |
| 事前申請ID | ? | ? |
| 事前申請金額 | ? | ? |
| 仮払希望額 | ? | ? |
| 仮払期日 | ? | ? |
| 仮払各定額 | ? | ? |

次に detail/customized_items の各要素の `title` をカラム名、 `content` を値として追加（末尾を除く）

コメント

| カラム名 | キー | 変換方法 |
| --- | --- | --- |
| 明細の名前 | ? | ? |
| 交通費明細の内訳 | detail/expense/specifics/rows の breakdown | そのまま |
| 交通費明細の利用日 | detail/expense/specifics/rows の use_date | "YYYY/M/D" |
| 交通費明細の出発 | ? | ? |
| 交通費明細の到着 | ? | ? |
| 交通費明細の往復 | ? | ? |
| 交通費明細の交通手段 | ? | ? |
| 交通費明細の金額 | detail/expense/specifics/rows の amount | そのまま |
| 交通費明細の目的・備考 | detail/expense/specifics/rows の content_description | そのまま |
| 交通費明細のグループ | detail/expense/specifics/rows の group_name | そのまま |
| 交通費明細のプロジェクト | detail/expense/specifics/rows の project_name | そのまま |
| 交通費明細の支払先 | ? | ? |
| 交通費明細の支払先登録番号 | ? | ? |
| 交通費明細の区分 | ? | ? |

#### 書式 4-1 (form_id = 41052205)

申請ID, 申請ステータス, 最終承認日, 承認者, フォーム名, タイトル, 申請者メールアドレス, 申請者コード, 申請者名（姓）, 申請者名（名）, 申請日時, 関連プロジェクト名, 関連グループ名

| カラム名 | キー | 変換方法 |
| --- | --- | --- |
| 関連申請タイトル | detail/payment/related_request_title | そのまま |
| 関連申請ID | detail/payment/related_request_id | そのまま |
| 事前申請タイトル | ? | ? |
| 事前申請ID | ? | ? |
| 支払い依頼の内訳 | ? | ? |
| 計上日 | ? | ? |
| 金額 | total_amount | そのまま |
| 内容 | detail/payment/content_description | そのまま |
| 支払い予定日 | pay_at | "YYYY/M/D H:MM:SS" |
| 振込手数料 | ? | "当方負担" のみ? |
| 源泉徴収税 | ? | ? |

次に支払先名などの情報を追加するが、どのキーから対応付けるかは不明

| カラム名 | キー | 変換方法 |
| --- | --- | --- |
| 支払先名 | company/company_name | そのまま |
| 支払先登録番号 | company/invoice_registrated_number | そのまま |
| 銀行コード | company/bank_code | int(bank_code) |
| 銀行名 | company/bank_name | そのまま |
| 支店コード | company/branch_code | int(branch_code) |
| 支店名 | company/branch_name | そのまま |
| 口座種別 | company_bank_account_type_code | {"1": "普通", "2": "当座", "9": "その他"} |
| 口座番号 | company/bank_account_code | int(bank_account_code) |
| 口座名 | company/bank_account_name_kana | そのまま |

次に detail/customized_items の各要素の `title` をカラム名、 `content` を値として追加（末尾から2番目の要素を除く）

コメント

#### 書式 4-4 (form_id = 9782279)

申請ID, 申請ステータス, 最終承認日, 承認者, フォーム名, タイトル, 申請者メールアドレス, 申請者コード, 申請者名（姓）, 申請者名（名）, 申請日時, 関連プロジェクト名, 関連グループ名

以降は customized_items の各要素の `title` をカラム名、 `content` を値として追加．ただし"金額"、"源泉徴収税額"については "123,456 円" の形式から "123456" に変換．

最後に コメント
