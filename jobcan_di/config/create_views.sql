-- ************************************************************
-- For users api
-- ************************************************************

-- users, user_bank_accounts

CREATE VIEW IF NOT EXISTS view_user_details AS
SELECT
    u.user_code,
    u.email,
    u.last_name,
    u.first_name,
    u.is_approver,
    u.user_role,
    u.memo,
    uba.bank_code,
    uba.bank_name,
    uba.bank_name_kana,
    uba.branch_code,
    uba.branch_name,
    uba.branch_name_kana,
    uba.bank_account_type_code,
    uba.bank_account_code,
    uba.bank_account_name_kana
FROM
    users u
LEFT JOIN
    user_bank_accounts uba ON u.id = uba.user_id;

-- user_groups, user_positions

CREATE VIEW IF NOT EXISTS view_user_group_position AS
SELECT
    u.user_code,
    ug.group_code,
    up.position_code
FROM
    users u
JOIN
    user_groups ug ON u.id = ug.user_id
LEFT JOIN
    user_positions up ON u.id = up.user_id AND ug.group_code = up.group_code;

-- ************************************************************
-- For groups api
-- ************************************************************

CREATE VIEW IF NOT EXISTS view_groups AS
SELECT
    g.group_code,
    g.group_name,
    g.parent_group_code,
    g.description
FROM
    groups g;

-- ************************************************************
-- For positions api
-- ************************************************************

CREATE VIEW IF NOT EXISTS view_positions AS
SELECT
    p.position_code,
    p.position_name,
    p.description
FROM
    positions p;

-- ************************************************************
-- For projects api
-- ************************************************************

/* TODO: Add view for projects api */

-- ************************************************************
-- For forms api
-- ************************************************************

CREATE VIEW IF NOT EXISTS view_forms AS
SELECT
    f.id,
    f.category,
    f.form_type,
    f.settlement_type,
    f.name,
    f.view_type,
    f.description
FROM
    forms f;

-- ************************************************************
-- For companies api
-- ************************************************************

-- companies (Convert string to integer, but '' to NULL)
/* TODO: Check CASE for bank_account_type_code */

CREATE VIEW IF NOT EXISTS view_companies AS
SELECT
    c.company_code,
    c.company_name,
    c.zip_code,
    c.address,
    CAST(NULLIF(c.bank_code, '') AS INTEGER) AS bank_code,
    c.bank_name,
    CAST(NULLIF(c.branch_code, '') AS INTEGER) AS branch_code,
    c.branch_name,
    CASE c.bank_account_type_code
        WHEN NULL THEN NULL
		WHEN '' THEN NULL
        WHEN '1' THEN '普通'
        WHEN '2' THEN '当座'
		WHEN '9' THEN 'その他'
        ELSE CAST(c.bank_account_type_code AS INTEGER)
    END AS bank_account_type_code,
    CAST(NULLIF(c.bank_account_code, '') AS INTEGER) AS bank_account_code,
    c.bank_account_name_kana,
    c.invoice_registrated_number
FROM
    companies c;

-- ************************************************************
-- For requests api
-- ************************************************************

CREATE VIEW IF NOT EXISTS view_request_details AS
SELECT
    r.id,
    r.title,
    CASE r.status
        WHEN 'in_progress' THEN '進行中'
        WHEN 'completed' THEN '完了'
        WHEN 'rejected' THEN '却下'
        WHEN 'canceled' THEN '取り消し'
        WHEN 'returned' THEN '差し戻し'
        WHEN 'canceled_after_completion' THEN '完了後取消'
        ELSE status  -- 未知のステータスの場合は元の値を表示
    END AS status,
    r.form_id,
    r.form_name,
    r.form_type,
    r.settlement_type,
    strftime('%Y/%m/%d  %H:%M:%S', r.applied_date, 'localtime') AS applied_date,
    r.applicant_code,
    r.applicant_last_name,
    r.applicant_first_name,
    r.applicant_group_name,
    r.applicant_group_code,
    r.applicant_position_name,
    r.proxy_applicant_last_name,
    r.proxy_applicant_first_name,
    r.group_name,
    r.group_code,
    r.project_name,
    r.project_code,
    r.flow_step_name,
    r.is_content_changed,
    r.total_amount,
    r.pay_at,
    r.final_approval_period,
    strftime('%Y/%m/%d  %H:%M:%S', r.final_approved_date, 'localtime') AS final_approved_date,
    exp.amount,
    exp.related_request_title AS expense_related_request_title,
    exp.related_request_id AS expense_related_request_id,
    exp.use_suspense_payment AS expense_use_suspense_payment,
    exp.content_description AS expense_content_description,
    exp.advanced_payment AS expense_advanced_payment,
    exp.suspense_payment_amount AS expense_suspense_payment_amount,
    ec.related_request_id AS ec_related_request_id,
    ec.related_request_title AS ec_related_request_title,
    ec.content_description AS ec_content_description,
    ec.billing_destination AS ec_billing_destination
FROM
    requests r
LEFT JOIN
    expense exp ON r.id = exp.request_id
LEFT JOIN
    ec ON r.id = ec.request_id;

-- approval_process, approval_steps, approvers

CREATE VIEW IF NOT EXISTS view_approval_process AS
SELECT
    ap.request_id,
    ast.step_index,
    ast.name,
    ast.condition,
    ast.status AS final_status,
    av.status AS approver_status,
    av.approver_index,
    av.approved_date,
    av.approver_name,
    av.approver_code
FROM
    approval_process ap
LEFT JOIN
    approval_steps ast ON ast.approval_process_id = ap.id
LEFT JOIN
    approvers av ON av.approval_step_id = ast.id;

-- expense_specifics, expense_specific_rows

CREATE VIEW IF NOT EXISTS view_expense_specifics AS
SELECT
    e.request_id,
    es.type,
    es.col_number,
    CAST(esr.row_number AS INTEGER) AS "row_number",
    esr.use_date,
    esr.group_name,
    esr.project_name,
    esr.content_description,
    esr.breakdown,
    esr.amount
FROM
    expense e
LEFT JOIN
    expense_specifics es ON e.id = es.expense_id
LEFT JOIN
    expense_specific_rows esr ON es.id = esr.expense_specific_id;

-- ************************************************************
-- For preparing to export CSV view
-- ************************************************************

-- customized_items

CREATE VIEW IF NOT EXISTS view_form_items AS
SELECT
    r.form_id,
    r.form_name,
    ci.title,
    ci.item_index
FROM
    customized_items ci
JOIN
    requests r ON ci.request_id = r.id
GROUP BY
    r.form_id, ci.item_index
ORDER BY
    r.form_id, ci.item_index;

CREATE VIEW IF NOT EXISTS view_form_items_by_name AS
SELECT
    r.form_id,
    r.form_name,
    ci.title,
    ci.item_index
FROM
    customized_items ci
JOIN
    requests r ON ci.request_id = r.id
GROUP BY
    r.form_id, ci.title
ORDER BY
    r.form_id, ci.item_index;

-- approvers ("承認者"のカラムを追加)

CREATE VIEW IF NOT EXISTS view_request_approval_history AS
SELECT
    request_id,
    GROUP_CONCAT(approver_detail, ', ') AS approver_details
FROM (
    SELECT
        request_id,
        approver_name ||
            '（承認日時：' ||
            strftime('%Y/%m/%d  %H:%M:%S',
                     approved_date, 'localtime') ||
            '）' AS approver_detail
    FROM
        view_approval_process
    WHERE
        approver_status = '承認済み'  -- 承認済みのステータスのみを対象とする
    ORDER BY
        request_id,
        approved_date
)
GROUP BY
    request_id;

-- ************************************************************
-- For CSV export
-- ************************************************************

-- ************************************************************
-- Format 3
-- ************************************************************

-- 立替精算全般

CREATE VIEW IF NOT EXISTS "view_立替精算(書式3)" AS
SELECT
    r.id AS "申請ID",
    r.status AS "申請ステータス",
    r.final_approved_date AS "最終承認日",
    rah.approver_details AS "承認者",
	r.form_id AS "フォームID",
    r.form_name AS "フォーム名",
    r.title AS "タイトル",
    u.email AS "申請者メールアドレス",
    r.applicant_code AS "申請者コード",
    r.applicant_last_name AS "申請者名（姓）",
    r.applicant_first_name AS "申請者名（名）",
    r.applied_date AS "申請日時",
    r.group_name AS "関連グループ名",
    r.project_name AS "関連プロジェクト名",
    MAX(CASE WHEN es.col_number = 0 AND es.row_number = 1 THEN es.breakdown END) AS "経費の内訳",
    MAX(CASE WHEN es.col_number = 0 AND es.row_number = 1 THEN es.use_date END) AS "利用日",
    r.total_amount AS "金額",
    -- 内容
    -- 支払先名
    -- 支払先登録番号
    -- 支払方法
    -- 事前申請タイトル
    -- 事前申請ID
    -- 事前申請金額
    -- 仮払希望額
    -- 仮払期日
    -- 仮払支払確定額
    MAX(CASE WHEN ci.item_index = 0 THEN ci.content END) AS "備考",
    MAX(CASE WHEN ci.item_index = 1 THEN ci.content END) AS "【申請にあたっての確認事項】"
    -- コメント
FROM
    view_request_details r
LEFT JOIN
    customized_items ci ON r.id = ci.request_id
LEFT JOIN
    users u ON r.applicant_code = u.user_code
LEFT JOIN
    view_request_approval_history rah ON r.id = rah.request_id
LEFT JOIN
    view_expense_specifics es ON r.id = es.request_id
WHERE
    r.form_id IN(14789304, 21063509, 39901682, 54142953, 64039825, 66265686, 70659861, 84927058, 87208398, 88302404)
GROUP BY
    r.id;

CREATE VIEW IF NOT EXISTS "view_立替精算(書式3)_明細" AS
SELECT
    r.id AS "申請ID",
    -- 明細の名前
    es.breakdown AS "交通費明細の内訳",
    es.use_date AS "交通費明細の利用日",
    -- 交通費明細の出発
    -- 交通費明細の到着
    -- 交通費明細の往復
    -- 交通費明細の交通手段
    es.amount AS "交通費明細の金額",
    es.content_description AS "交通費明細の目的・備考",
    es.group_name AS "交通費明細のグループ",
    es.project_name AS "交通費明細のプロジェクト"
    -- 交通費明細の支払先
    -- 交通費明細の支払先登録番号
    -- 交通費明細の区分
FROM
    view_request_details r
LEFT JOIN
    view_expense_specifics es ON r.id = es.request_id
WHERE
    r.form_id IN(14789304, 21063509, 39901682, 54142953, 64039825, 66265686, 70659861, 84927058, 87208398, 88302404)
ORDER BY
    "申請ID", "交通費明細の利用日";

-- 立替精算・交通費(書式3-3.) : form_id = 54142953

CREATE VIEW IF NOT EXISTS "view_立替精算・交通費(書式3-3.)" AS
SELECT
    *
FROM
    "view_立替精算(書式3)" r
WHERE
    r."フォームID" = '54142953';

CREATE VIEW IF NOT EXISTS "view_立替精算・交通費(書式3-3.)_明細" AS
SELECT
    r.id AS "申請ID",
    -- 明細の名前
    es.breakdown AS "交通費明細の内訳",
    es.use_date AS "交通費明細の利用日",
    -- 交通費明細の出発
    -- 交通費明細の到着
    -- 交通費明細の往復
    -- 交通費明細の交通手段
    es.amount AS "交通費明細の金額",
    es.content_description AS "交通費明細の目的・備考",
    es.group_name AS "交通費明細のグループ",
    es.project_name AS "交通費明細のプロジェクト"
    -- 交通費明細の支払先
    -- 交通費明細の支払先登録番号
    -- 交通費明細の区分
FROM
    view_request_details r
LEFT JOIN
    view_expense_specifics es ON r.id = es.request_id
WHERE
    r.form_id = '54142953'
ORDER BY
    "申請ID", "交通費明細の利用日";

-- ************************************************************
-- Format 4
-- ************************************************************

-- 支払依頼申請書（書式4-1. 支払・請求書） : form_id = 41052205

CREATE VIEW IF NOT EXISTS "view_支払依頼申請書（書式4-1. 支払・請求書）" AS
SELECT
    r.id AS "申請ID",
    r.status AS "申請ステータス",
    r.final_approved_date AS "最終承認日",
    rah.approver_details AS "承認者",
    r.form_name AS "フォーム名",
    r.title AS "タイトル",
    u.email AS "申請者メールアドレス",
    r.applicant_code AS "申請者コード",
    r.applicant_last_name AS "申請者名（姓）",
    r.applicant_first_name AS "申請者名（名）",
    r.applied_date AS "申請日時",
    r.project_name AS "関連プロジェクト名",
    r.group_name AS "関連グループ名",
    p.related_request_title AS "関連申請タイトル",
    p.related_request_id AS "関連申請ID",
    -- 事前申請タイトル
    -- 事前申請ID
    -- 支払い依頼の内訳
    fjb.journal_date AS "計上日",
    r.total_amount AS "金額",
    p.content_description AS "内容",
    fjp.journal_date AS "支払予定日",
    -- 振込手数料
    -- 源泉徴収税
	fjp.company_code AS "支払先コード",
    fjp.company_name AS "支払先名",
    fjp.invoice_registrated_number AS "支払先登録番号",
    cp.bank_code AS "銀行コード",
    cp.bank_name AS "銀行名",
    cp.branch_code AS "支店コード",
    cp.branch_name AS "支店名",
    CAST(
        REPLACE(REPLACE(REPLACE(MAX(CASE WHEN ci.item_index = 0 THEN ci.content END), '円', ''), ',', ''), ' ', '')
    AS INTEGER) AS "源泉徴収税額",
    MAX(CASE WHEN ci.item_index = 1 THEN ci.content END) AS "請求書の添付",
    MAX(CASE WHEN ci.item_index = 2 THEN ci.content END) AS "請求書の受取方法",
    MAX(CASE WHEN ci.item_index = 3 THEN ci.content END) AS "支払頻度",
    MAX(CASE WHEN ci.item_index = 4 THEN ci.content END) AS "備考",
    MAX(CASE WHEN ci.item_index = 5 THEN ci.content END) AS "【申請にあたっての確認事項】",
    MAX(CASE WHEN ci.item_index = 7 THEN ci.content END) AS "新しい項目"
    -- コメント
FROM
    view_request_details r
LEFT JOIN
    customized_items ci ON r.id = ci.request_id
LEFT JOIN
    users u ON r.applicant_code = u.user_code
LEFT JOIN
    fix_journals fjb ON fjb.view_id = r.id AND fjb.journal_type = "book"
LEFT JOIN
    fix_journals fjp ON fjp.view_id = r.id AND fjp.journal_type = "pay"
LEFT JOIN
    view_companies cp ON cp.company_name = fjp.company_name
LEFT JOIN
    payment p ON r.id = p.request_id
LEFT JOIN
    view_request_approval_history rah ON r.id = rah.request_id
WHERE
    r.form_id = '41052205'
GROUP BY
    r.id, r.title, r.status, r.final_approved_date;

-- 支払依頼申請書（書式4-2. 社員振込） : form_id = 75858728
-- NOTE: 祝金などの個人を対象とした振込の場合、fix_journalからも支払先が取得できないケースがほとんど。支払日は取得可能

CREATE VIEW IF NOT EXISTS "view_支払依頼申請書（書式4-2. 社員振込）" AS
SELECT
    r.id AS "申請ID",
    r.status AS "申請ステータス",
    r.final_approved_date AS "最終承認日",
    rah.approver_details AS "承認者",
    r.form_name AS "フォーム名",
    r.title AS "タイトル",
    u.email AS "申請者メールアドレス",
    r.applicant_code AS "申請者コード",
    r.applicant_last_name AS "申請者名（姓）",
    r.applicant_first_name AS "申請者名（名）",
    r.applied_date AS "申請日時",
    r.project_name AS "関連プロジェクト名",
    r.group_name AS "関連グループ名",
    p.related_request_title AS "関連申請タイトル",
    p.related_request_id AS "関連申請ID",
    -- 事前申請タイトル
    -- 事前申請ID
    -- 支払い依頼の内訳
    fjb.journal_date AS "計上日",
    r.total_amount AS "金額",
    p.content_description AS "内容",
    fjp.journal_date AS "支払予定日",
    -- 振込手数料
    -- 源泉徴収税
	fjp.company_code AS "支払先コード",
    fjp.company_name AS "支払先名",
    fjp.invoice_registrated_number AS "支払先登録番号",
    cp.bank_code AS "銀行コード",
    cp.bank_name AS "銀行名",
    cp.branch_code AS "支店コード",
    cp.branch_name AS "支店名",
    cp.bank_account_type_code AS "口座種別",
    cp.bank_account_code AS "口座番号",
    cp.bank_account_name_kana AS "口座名",
    MAX(CASE WHEN ci.item_index = 0 THEN ci.content END) AS "備考",
    MAX(CASE WHEN ci.item_index = 1 THEN ci.content END) AS "【申請にあたっての確認事項】"
    -- コメント
FROM
    view_request_details r
LEFT JOIN
    customized_items ci ON r.id = ci.request_id
LEFT JOIN
    users u ON r.applicant_code = u.user_code
LEFT JOIN
    fix_journals fjb ON fjb.view_id = r.id AND fjb.journal_type = "book"
LEFT JOIN
    fix_journals fjp ON fjp.view_id = r.id AND fjp.journal_type = "pay"
LEFT JOIN
    view_companies cp ON cp.company_name = fjp.company_name
LEFT JOIN
    payment p ON r.id = p.request_id
LEFT JOIN
    view_request_approval_history rah ON r.id = rah.request_id
WHERE
    r.form_id = '75858728'
GROUP BY
    r.id;

-- 支払依頼申請書（書式4-3. 窓口・コンビニ払い） : form_id = 11171823

CREATE VIEW IF NOT EXISTS "view_支払依頼申請書（書式4-3. 窓口・コンビニ払い）" AS
SELECT
    r.id AS "申請ID",
    r.status AS "申請ステータス",
    r.final_approved_date AS "最終承認日",
    rah.approver_details AS "承認者",
    r.form_name AS "フォーム名",
    r.title AS "タイトル",
    u.email AS "申請者メールアドレス",
    r.applicant_code AS "申請者コード",
    r.applicant_last_name AS "申請者名（姓）",
    r.applicant_first_name AS "申請者名（名）",
    r.applied_date AS "申請日時",
    r.project_name AS "関連プロジェクト名",
    r.group_name AS "関連グループ名",
    MAX(CASE WHEN ci.item_index = 0 THEN ci.content END) AS "関連申請",
    MAX(CASE WHEN ci.item_index = 1 THEN ci.content END) AS "計上日",
    CAST(
        REPLACE(REPLACE(REPLACE(MAX(CASE WHEN ci.item_index = 2 THEN ci.content END), '円', ''), ',', ''), ' ', '')
    AS INTEGER) AS "金額",
    MAX(CASE WHEN ci.item_index = 3 THEN ci.content END) AS "内容",
    MAX(CASE WHEN ci.item_index = 4 THEN ci.content END) AS "支払先選択",
    MAX(CASE WHEN ci.item_index = 5 THEN ci.content END) AS "取引先名（既存）",
    MAX(CASE WHEN ci.item_index = 6 THEN ci.content END) AS "取引先名（新規）",
    MAX(CASE WHEN ci.item_index = 7 THEN ci.content END) AS "支払日",
    MAX(CASE WHEN ci.item_index = 8 THEN ci.content END) AS "振込手数料",
    MAX(CASE WHEN ci.item_index = 9 THEN ci.content END) AS "源泉徴収税",
    CAST(
        REPLACE(REPLACE(REPLACE(MAX(CASE WHEN ci.item_index = 10 THEN ci.content END), '円', ''), ',', ''), ' ', '')
    AS INTEGER) AS "源泉徴収税額",
    MAX(CASE WHEN ci.item_index = 11 THEN ci.content END) AS "請求書の添付",
    MAX(CASE WHEN ci.item_index = 12 THEN ci.content END) AS "請求書の受取方法",
    MAX(CASE WHEN ci.item_index = 13 THEN ci.content END) AS "支払い頻度",
    MAX(CASE WHEN ci.item_index = 14 THEN ci.content END) AS "備考",
    MAX(CASE WHEN ci.item_index = 15 THEN ci.content END) AS "【申請にあたっての確認事項】"
    -- コメント
FROM
    view_request_details r
LEFT JOIN
    customized_items ci ON r.id = ci.request_id
LEFT JOIN
    users u ON r.applicant_code = u.user_code
LEFT JOIN
    view_request_approval_history rah ON r.id = rah.request_id
WHERE
    r.form_id = '11171823'
GROUP BY
    r.id;

-- 支払依頼申請書（書式4-4. 口座振替） : form_id = 9782279

CREATE VIEW IF NOT EXISTS "view_支払依頼申請書（書式4-4. 口座振替）" AS
SELECT
    r.id AS "申請ID",
    r.status AS "申請ステータス",
    r.final_approved_date AS "最終承認日",
    rah.approver_details AS "承認者",
    r.form_name AS "フォーム名",
    r.title AS "タイトル",
    u.email AS "申請者メールアドレス",
    r.applicant_code AS "申請者コード",
    r.applicant_last_name AS "申請者名（姓）",
    r.applicant_first_name AS "申請者名（名）",
    r.applied_date AS "申請日時",
    r.project_name AS "関連プロジェクト名",
    r.group_name AS "関連グループ名",
    MAX(CASE WHEN ci.item_index = 0 THEN ci.content END) AS "関連申請",
    MAX(CASE WHEN ci.item_index = 1 THEN ci.content END) AS "支払の内訳",
    MAX(CASE WHEN ci.item_index = 2 THEN ci.content END) AS "計上日",
    CAST(
        REPLACE(REPLACE(REPLACE(MAX(CASE WHEN ci.item_index = 3 THEN ci.content END), '円', ''), ',', ''), ' ', '')
    AS INTEGER) AS "金額",
    MAX(CASE WHEN ci.item_index = 4 THEN ci.content END) AS "内容",
    MAX(CASE WHEN ci.item_index = 5 THEN ci.content END) AS "支払先選択",
    MAX(CASE WHEN ci.item_index = 6 THEN ci.content END) AS "取引先名（既存）",
    MAX(CASE WHEN ci.item_index = 7 THEN ci.content END) AS "取引先名（新規）",
    MAX(CASE WHEN ci.item_index = 8 THEN ci.content END) AS "支払日",
    MAX(CASE WHEN ci.item_index = 9 THEN ci.content END) AS "振込手数料",
    MAX(CASE WHEN ci.item_index = 10 THEN ci.content END) AS "源泉徴収税",
    CAST(
        REPLACE(REPLACE(REPLACE(MAX(CASE WHEN ci.item_index = 11 THEN ci.content END), '円', ''), ',', ''), ' ', '')
    AS INTEGER) AS "源泉徴収税額",
    MAX(CASE WHEN ci.item_index = 12 THEN ci.content END) AS "請求書の添付",
    MAX(CASE WHEN ci.item_index = 13 THEN ci.content END) AS "請求書の受取方法",
    MAX(CASE WHEN ci.item_index = 14 THEN ci.content END) AS "支払頻度",
    MAX(CASE WHEN ci.item_index = 15 THEN ci.content END) AS "備考"
FROM
    view_request_details r
LEFT JOIN
    customized_items ci ON r.id = ci.request_id
LEFT JOIN
    users u ON r.applicant_code = u.user_code
LEFT JOIN
    view_request_approval_history rah ON r.id = rah.request_id
WHERE
    r.form_id = '9782279'
GROUP BY
    r.id, r.title, r.status, r.final_approved_date;

-- コーポレートカード領収書提出フォーム（書式4-5.） : form_id = 29608169

CREATE VIEW IF NOT EXISTS "view_支払依頼申請書（書式4-5. コーポレートカード領収書提出）" AS
SELECT
    r.id AS "申請ID",
    r.status AS "申請ステータス",
    r.final_approved_date AS "最終承認日",
    rah.approver_details AS "承認者",
    r.form_name AS "フォーム名",
    r.title AS "タイトル",
    u.email AS "申請者メールアドレス",
    r.applicant_code AS "申請者コード",
    r.applicant_last_name AS "申請者名（姓）",
    r.applicant_first_name AS "申請者名（名）",
    r.applied_date AS "申請日時",
    r.project_name AS "関連プロジェクト名",
    r.group_name AS "関連グループ名",
    MAX(CASE WHEN ci.item_index = 0 THEN ci.content END) AS "関連申請",
    MAX(CASE WHEN ci.item_index = 1 THEN ci.content END) AS "カードの種類",
    MAX(CASE WHEN ci.item_index = 2 THEN ci.content END) AS "支払の内訳",
    MAX(CASE WHEN ci.item_index = 3 THEN ci.content END) AS "計上日",
    CAST(
        REPLACE(REPLACE(REPLACE(MAX(CASE WHEN ci.item_index = 4 THEN ci.content END), '円', ''), ',', ''), ' ', '')
    AS INTEGER) AS "金額",
    MAX(CASE WHEN ci.item_index = 5 THEN ci.content END) AS "内容",
    MAX(CASE WHEN ci.item_index = 6 THEN ci.content END) AS "支払先名",
    -- 支払先の種類
    MAX(CASE WHEN ci.item_index = 7 THEN ci.content END) AS "決済日",
    MAX(CASE WHEN ci.item_index = 8 THEN ci.content END) AS "領収書等の添付",
    MAX(CASE WHEN ci.item_index = 9 THEN ci.content END) AS "領収書等の受取方法",
    MAX(CASE WHEN ci.item_index = 10 THEN ci.content END) AS "支払頻度",
    MAX(CASE WHEN ci.item_index = 11 THEN ci.content END) AS "備考"
    -- コメント
FROM
    view_request_details r
LEFT JOIN
    customized_items ci ON r.id = ci.request_id
LEFT JOIN
    users u ON r.applicant_code = u.user_code
LEFT JOIN
    view_request_approval_history rah ON r.id = rah.request_id
WHERE
    r.form_id = '29608169'
GROUP BY
    r.id;
