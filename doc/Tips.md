# Tips

> [全体の目次に戻る](../README.md)

## 目次

- [目次](#目次)
- [実行に際して](#実行に際して)
  - [アプリケーションのビルド](#アプリケーションのビルド)
    - [オプションの説明](#オプションの説明)
- [データベースなどとの接続](#データベースなどとの接続)
  - [Power BI (Service) を介した接続](#power-bi-service-を介した接続)
    - [On-premises Data Gateway のインストール](#on-premises-data-gateway-のインストール)
    - [SQLite ODBC Driver のインストール](#sqlite-odbc-driver-のインストール)
    - [ODBC Data Source の設定](#odbc-data-source-の設定)
    - [Power BI の設定](#power-bi-の設定)
  - [Excel との接続](#excel-との接続)
    - [SQLite ODBC Driver のインストール (再)](#sqlite-odbc-driver-のインストール-再)
    - [ODBC Data Source の設定 (再)](#odbc-data-source-の設定-再)
    - [Excel での設定](#excel-での設定)
- [データの説明](#データの説明)
  - [仕訳情報（fix\_journalsテーブル）](#仕訳情報fix_journalsテーブル)
    - [カラムの説明](#カラムの説明)
    - [テーブルの読み方](#テーブルの読み方)

## 実行に際して

### アプリケーションのビルド

　本アプリケーションは`nuitka`を用いてビルドしています。nuitkaが未インストールの場合は`pip install nuitka`を実行した後、本体 (`main.py`) のビルドに以下のコマンドを実行してください。

```bash
nuitka --windows-console-mode=disable --standalone --follow-imports main.py
```

　また、`コンフィグ設定用のGUIをビルドする際は以下のコマンドを実行してください。

```bash
nuitka --windows-console-mode=disable --standalone --follow-imports --enable-plugin=tk-inter config_gui.py
```

#### オプションの説明

| オプション | 説明 |
| --- | --- |
| `--windows-console-mode=disable` | Windows環境でコンソールを非表示にします。 |
| `--standalone` | 依存ライブラリを同梱します（Python環境のない場所でも動かせるようにします）。 |
| `--follow-imports` | 利用しているモジュールを自動的に検出します。 |
| `--enable-plugin=tk-inter` | Tkinterを使用する場合に指定します。 |

## データベースなどとの接続

### Power BI (Service) を介した接続

Power BI Service（EdgeやChromeなどのブラウザからアクセスするPower BI）と、ローカルのSQLデータベースを接続する方法についての説明です。

デスクトップ上で動かすPower BI Desktopとは手順が少し異なります。Power BI Desktopの場合については、[Excel との接続](#excel-との接続)および[このサイト](https://zenn.dev/yumizz/articles/7766b035673b2f)などを参考にしてください。

#### On-premises Data Gateway のインストール

Power BI Serviceからローカルのデータベースにアクセスするためには、オンプレミスデータゲートウェイをインストールする必要があります。以下のサイトにアクセスし、ダウンロードを行います。

https://go.microsoft.com/fwlink/?LinkId=2116849&clcid=0x409

途中でサインインを求められる場合があります。その際は、Power Bi Serviceのログインに使用しているアカウント（組織アカウント）でサインインしてください。次の画面で「このコンピューターに新しいゲートウェイを登録します」を選択します。

<img src="img/tips/image-18.png" alt="alt text" width=75%>

図. サインイン画面[*](https://learn.microsoft.com/ja-jp/data-integration/gateway/service-gateway-install)

ゲートウェイの名前と回復キーの設定を行います。ゲートウェイの名前は全体で一意である必要があります。ここで設定したキーが[Power BIの設定](#power-bi-の設定)で使用されます。

<img src="img/tips/image-19.png" alt="alt text" width=75%>

図. ゲートウェイの設定画面[*](https://learn.microsoft.com/ja-jp/data-integration/gateway/service-gateway-install)

以下のような画面が表示されればインストールは完了です。

<img src="img/tips/image-20.png" alt="alt text" width=50%>

#### SQLite ODBC Driver のインストール

以下のサイトにアクセスし、ドライバーをインストールします。インストール可能なバージョンには32bit（`sqliteodbc.exe`）と64bit（`sqliteodbc_w64.exe`）の2種類があり、オンプレミスデータゲートウェイと合わせる必要があります。本稿では、64bitのオンプレミスデータゲートウェイをインストールしたとしてセットアップを進めます。

http://www.ch-werner.de/sqliteodbc/

<img src="img/tips/image-10.png" alt="alt text" width=50%>

図. サイト上のドライバーの種類

> bit 数を合わせない場合、Power BI での接続の際に以下のようなエラーが発生することがあります。
>
> <img src="img/tips/image-11.png" alt="alt text" width=75%>

ダウンロードしたファイルを実行し、インストールを開始します。起動時に管理者権限が要求されます。

<img src="img/tips/image-12.png" alt="alt text" width=75%>

図. インストール画面

いくつかの画面を進めると、以下の画面が表示されます。`Sqlite 2 Drivers`にチェックを入れ、`Install`をクリックしてください。これでSQLite ODBC Driverのインストールは完了です。

<img src="img/tips/image-13.png" alt="alt text" width=75%>

#### ODBC Data Source の設定

Windowsの検索欄から`ODBC データ ソース (64 ビット)`を検索し、これを実行します。

<img src="img/tips/image-14.png" alt="alt text" width=60%>

> [ODBC Driver](#sqlite-odbc-driver-のインストール)と同様に、オンプレミスデータゲートウェイと同じbit数のものを起動します。

以下のような画面が開くので、「**システム DSN**」タブから「追加」ボタンをクリックし、先ほどインストールしたドライバーを選択します。

<img src="img/tips/image.png" alt="alt text" width=75%>

本アプリケーションはSQLite3を扱うため、「SQLite3 ODBC Driver」を選択します。

<img src="img/tips/image-2.png" alt="alt text" width=75%>

次に以下のような画面が表示されるため、`Data Source Name`には適当な名前（以下では`JobcanDI`としています）を、`Database Name`には本アプリケーションの作成する`jobcan-data.db`のパスを入力します。後者に関しては、右の`Browse...`から当該ファイルを選択するのが簡単です。

以上を入力後、「OK」を選択します。

<img src="img/tips/image-1.png" alt="alt text" width=60%>

システムDSNに`JobcanDI`が追加されました。

<img src="img/tips/image-15.png" alt="alt text" width=75%>

#### Power BI の設定

PowerBIから、適当なワークスペースを選択、または作成します。今回は、`ジョブカン`ワークスペースを作成しました。

<img src="img/tips/image-5.png" alt="alt text" width=75%>

左上の「新規」ボタンから「データフロー」を選択します。

<img src="img/tips/image-6.png" alt="alt text" width=75%>

以下のような画面に遷移するので、次に「新しいテーブルの追加」を選択します。

<img src="img/tips/image-7.png" alt="alt text" width=75%>

データソースとして「ODBC」を選択します。

<img src="img/tips/image-8.png" alt="alt text" width=75%>

ODBC接続文字列に、DSNとして[ODBCの設定](#odbc-data-source-の設定)で指定した名前（今回は`dsn=JobcanDI`）を指定します。

「新しい接続の作成」を選択し、データゲートウェイとしてパソコン上に作成したオンプレミスデータゲートウェイの名前を選択します。

また、認証の種類として`Windows`を選択し、本アプリケーションをダウンロードした「ユーザ名」と、そのユーザーの「パスワード」（ログイン時に使用するもの）を入力します。

<img src="img/tips/image-3.png" alt="alt text" width=75%>

以下のようにデータが読み込まれれば成功です。

<img src="img/tips/image-4.png" alt="alt text" width=75%>

> 認証の種類を匿名のままにした場合には、以下のようなエラーが発生することがあります（前に外部サーバとSSHトンネルを通して接続した環境で同様の設定を行った際には匿名で接続できたはずなのですが…）。
>
> `例外が発生しました: ODBC: ERROR [HY000] connect failed ERROR [IM006] [Microsoft][ODBC Driver Manager] ドライバーの SQLSetConnectAttr は失敗しました。`

### Excel との接続

本アプリケーションの作成したデータベースをExcelから読み込む方法を説明します。

また、デスクトップ上で動かすPower BI Desktopについてもおおよそ同じステップで同期が可能です。

#### SQLite ODBC Driver のインストール (再)

上記[SQLite ODBC Driverのインストール](#sqlite-odbc-driver-のインストール)で説明したように、ODBCドライバーをインストールします。

bit数については64bitのものを選択すればよいかと思います。

#### ODBC Data Source の設定 (再)

上記[ODBC Data Sourceの設定](#odbc-data-source-の設定)と同じようにして、DSNを設定します。注意点ですが、システムDSNではなく**ユーザーDSNを設定してください**。以下では、上記同様に`JobcanDI`として設定したとします。

#### Excel での設定

適当なシートを開き、「データ」タブから「データの取得」→「その他のデータソースから」→「ODBCから」を選択します。

<img src="img/tips/image-16.png" alt="alt text" width=75%>

データソースとして先ほど設定したユーザーDSN（`JobcanDI`）を選択します。ユーザー名とパスワードを聞かれた場合は、現在ログインしているユーザー名を入力してください。おそらくパスワードは入力しなくて大丈夫かと思います。

<img src="img/tips/image-9.png" alt="alt text" width=75%>

以下のような画面が開かれれば成功です。

<img src="img/tips/image-17.png" alt="alt text" width=75%>

## データの説明

### 仕訳情報（fix_journalsテーブル）

（2024/10/06 更新）

#### カラムの説明

　ジョブカン経費精算/ワークフローAPI（β版）（以下、API）では、以下の仕訳情報をそれぞれ対応するエンドポイントから取得できます。

- **確定済み未出力仕訳情報**：（確定済み未出力仕訳情報一覧 v1; `/v1/fix_journals/unprinted/`）

　取得したデータは本アプリケーションのデータベースの`fix_journals`テーブルに格納されます。各カラムの説明は以下の通りです。

| 分類 | カラム名 | 説明 |
| :-: | --- | --- |
| fix <br> journal <br> 固有 | journal_id | 仕訳ID |
| ^ | journal_type | `"book"`: 計上, `"pay"`: 支払 |
| ^ | journal_date | `"book"`の場合は計上日, `"pay"`の場合は支払(予定)日 |
| ^ | req_date <br> journal_summary <br> view_id <br> specifics_row_number | 対応する申請書の申請日、概要、申請ID（request_id）など |
| ^ | company_code <br> company_name | 支払先のコード、名前 |
| ^ | user_code <br> user_name | 申請者のコード、名前 |
| debit <br> (借方) | debit_account_title_code <br> debit_account_title_name | 借方：勘定科目 <br> 例）支払手数料 |
| ^ | debit_account_sub_title_code <br> debit_account_sub_title_name | 借方：補助科目 |
| ^ | debit_tax_category_code <br> debit_tax_category_name | 借方：税区分 <br> 例）課税仕入(10%)、対象外 |
| ^ | debit_amount <br> debit_tax_amount <br> debit_amount_without_tax | 借方：金額、税額、税抜金額 |
| ^ | debit_group_code <br> debit_group_name <br> debit_accounting_group_code | 借方：負担グループ <br> 例）管理部、全社 |
| ^ | debit_project_code <br> debit_project_name | 借方：負担プロジェクト |
| credit <br> (貸方) | 同上、credit_ で始まるカラム | 同上、貸方の情報 |

#### テーブルの読み方

　以下が申請ID`123456`に対応する仕訳情報であるとします（表A）。この場合、`fix_journals`には表Bのようなデータが格納されます。

**表A**．申請ID`123456`に対応する仕訳情報（例）

| | > | debit (借方) | > | credit (貸方) |
| :---: | --- | :---: | --- | :---: |
|   | 勘定科目 | 税抜金額 $+$ 税額 $=$ 金額 | 勘定科目 | 税抜金額 $+$ 税額 $=$ 金額 |
| 4/30 4月分計上 <br> book (計上) | **支払手数料** | $45360 + 4535 = 49895$ |  **未払金** | $49895 + 0 = 49895$ |
| ^ | **支払手数料** | $4641 + 464 = 5105$ |  **預り金** | $5105 + 0 = 5105$ |
| 5/31 5月分支払 <br> pay (支払) | **未払金** | $49895 + 0 = 49895$ |  **普通預金** | $49895 + 0 = 49895$ |

**表B**．`fix_journals`テーブルにおける、申請ID`123456`に対応する仕訳情報（例）．いくつかのカラムのみを抜粋

| journal_type | journal_date | req_date | view_id | debit_account_title_name | debit_amount | debit_tax_amount | debit_amount_without_tax | credit_account_title_name | ... |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| book | 2024/04/30 | 2024/04/18 | 123456 | 支払手数料 | 49895 | 4535 | 45360 | 未払金 | ... |
| book | 2024/04/30 | 2024/04/18 | 123456 | 支払手数料 | 5105 | 464 | 4641 | 預り金 | ... |
| pay | 2024/05/31 | 2024/04/18 | 123456 | 未払金 | 49895 | 0 | 49895 | 普通預金 | ... |


---

> [全体の目次に戻る](../README.md)

