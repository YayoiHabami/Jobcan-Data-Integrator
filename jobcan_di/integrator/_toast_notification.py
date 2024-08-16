"""
トースト通知関連のモジュール

Classes
-------
- `ToastProgressNotifier`: トースト通知を用いた進捗通知クラス

License
-------
MIT License

Original work Copyright (c) 2022 言葉
Modified work Copyright (c) 2024 Yayoi Habami

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from pathlib import Path
from typing import Optional, Union, Dict

from winsdk.windows.data.xml.dom import XmlDocument
from winsdk.windows.ui.notifications import (
    ToastNotification,
    ToastNotificationManager,
    NotificationData
)
from win11toast import (
    add_audio,
    add_button,
    add_icon,
    add_image,
    add_input,
    add_progress,
    add_selection,
    add_text,
    set_attribute,
    DEFAULT_APP_ID,
    xml,
    clear_toast
)

from .integrator_config import LogLevel
from .progress_status import (
    ProgressStatus, DetailedProgressStatus,
    get_progress_status_msg,
    PROGRESS_STATUS_MSG
)



def notify(title=None, body=None, on_click=print,
           icon=None, image=None, progress=None,
           audio=None, dialogue=None, duration=None,
           input_=None, inputs:Optional[list]=None, selection=None,
           selections:Optional[list]=None, button=None, buttons:Optional[list]=None,
           xml_=xml, app_id=DEFAULT_APP_ID, scenario=None,
           tag=None, group=None, suppress_popup=False):
    document = XmlDocument()
    document.load_xml(xml_.format(scenario=scenario if scenario else 'default'))
    if isinstance(on_click, str):
        set_attribute(document, '/toast', 'launch', on_click)

    if duration:
        set_attribute(document, '/toast', 'duration', duration)

    if title:
        add_text(title, document)
    if body:
        add_text(body, document)
    if input_:
        add_input(input_, document)
    if inputs:
        for _input in inputs:
            add_input(_input, document)
    if selection:
        add_selection(selection, document)
    if selections:
        for selection in selections:
            add_selection(selection, document)
    if button:
        add_button(button, document)
    if buttons:
        for button in buttons:
            add_button(button, document)
    if icon:
        add_icon(icon, document)
    if image:
        add_image(image, document)
    if progress:
        add_progress(progress, document)
    if audio:
        if isinstance(audio, str) and audio.startswith('ms'):
            add_audio(audio, document)
        elif isinstance(audio, str) and (path := Path(audio)).is_file():
            add_audio(f"file:///{path.absolute().as_posix()}", document)
        elif isinstance(audio, dict) and 'src' in audio and audio['src'].startswith('ms'):
            add_audio(audio, document)
        else:
            add_audio({'silent': 'true'}, document)
    if dialogue:
        add_audio({'silent': 'true'}, document)

    notification = ToastNotification(document)
    if progress:
        data = NotificationData()
        for name, value in progress.items():
            data.values[name] = str(value)
        data.sequence_number = 1
        notification.data = data
        notification.tag = 'my_tag'
        notification.suppress_popup = suppress_popup
    if tag:
        notification.tag = tag
    if group:
        notification.group = group
    if app_id == DEFAULT_APP_ID:
        try:
            notifier = ToastNotificationManager.create_toast_notifier()
        except Exception as e:
            notifier = ToastNotificationManager.create_toast_notifier(app_id)
    else:
        notifier = ToastNotificationManager.create_toast_notifier(app_id)
    notifier.show(notification)
    return notification




class ToastProgressNotifier:
    """トースト通知を用いた進捗通知クラス

    トースト通知を用いて進捗状況を通知するためのクラス"""
    def __init__(self, app_id=DEFAULT_APP_ID,
                 app_icon_path:Optional[Dict[LogLevel, str]]=None):
        """コンストラクタ

        Parameters
        ----------
        app_id : str, default DEFAULT_APP_ID
            通知アプリケーションのID
        app_icon_path : Optional[Dict[LogLevel, str]], default None
            通知アプリケーションのアイコンへのパス、LogLevel毎に指定"""
        self._app_id = app_id
        self._app_icon_path = app_icon_path

        self._notification_data = NotificationData()
        self._notifier = None

    def init_notification(
            self, title:str, body:str,
            duration:str="short", scenario="reminder", suppress_popup:bool=True
        ) -> None:
        """トースト通知の初期化

        Parameters
        ----------
        title : str
            通知のタイトル
        body : str
            通知の本文
        duration : str, default "short"
            通知の表示時間、
            "short", "long" が指定可能
        scenario : str, default "reminder"
            通知のシナリオ、
            "reminder", "alarm", "incomingCall", "urgent" が指定可能。
            "incomingCall" の場合、通知のタイムアウトが無効になる
        suppress_popup : bool, default True
            通知のポップアップを抑制するかどうか、
            `False` の場合、通知センターにのみ通知が表示される
        """
        # トースト通知の初期化
        notify(
            progress = {
                "title": "初期化中...",
                "status": "初期化中...",
                "value": 0,
                "valueStringOverride": "0%",
            },
            app_id = self._app_id,
            group = LogLevel.INFO.name,
            title = title,
            body = body,
            icon = self._app_icon_path[LogLevel.INFO] if self._app_icon_path else None,
            duration = duration,
            suppress_popup = suppress_popup,
            scenario = scenario
        )

        self._notifier = ToastNotificationManager.create_toast_notifier(self._app_id)

    def update(self,
               status:ProgressStatus,
               sub_status:DetailedProgressStatus,
               current:int, total:Union[int,None],
               sub_count:int=0, sub_total_count:int=0):
        """進捗状況を更新する

        Parameters
        ----------
        status : ProgressStatus
            大枠の進捗状況
        sub_status : DetailedProgressStatus
            細かい進捗状況、InitializingStatusなど
        current : int
            現在の進捗
        total : Union[int,None]
            全体の進捗
            Noneの場合、valueが0なら0%、それ以外なら100%として扱われる
        sub_count : int, default 0
            第2段階進捗に可算する値、基本的には0
            ProgressStatus.FORM_OUTLINEの場合に使用
        sub_total_count : int, default 0
            第2段階進捗の全体数に可算する値、基本的には0
            ProgressStatus.FORM_OUTLINEの場合に使用
        """
        # Notifier が未初期化の場合は何もしない (._init_notification()の呼び出し前)
        if self._notifier is None:
            return

        # sub_statusのメッセージを取得
        status_msg = get_progress_status_msg(status, sub_status, sub_count, sub_total_count)
        if total is None:
            value = 0 if current == 0 else 1
            str_value = f"{current}/?"
        elif total == 0:
            value = 1
            str_value = "0/0"
        else:
            value = current / total
            str_value = f"{current}/{total}"

        self._notification_data.values['title'] = PROGRESS_STATUS_MSG[status]
        self._notification_data.values['status'] = status_msg
        self._notification_data.values['value'] = str(value)
        self._notification_data.values['valueStringOverride'] = str_value
        self._notification_data.sequence_number = 2

        self._notifier.update(self._notification_data, 'my_tag', LogLevel.INFO.name)

    def notify(self, title:str, body:str,
               level:LogLevel=LogLevel.INFO,
               duration:str="short", scenario="reminder",
               suppress_popup:bool=True):
        """トースト通知を表示する

        Parameters
        ----------
        title : str
            通知のタイトル
        body : str
            通知の本文
        level : LogLevel, default LogLevel.INFO
            通知のレベル
        duration : str, default "short"
            通知の表示時間、
            "short", "long" が指定可能
        scenario : str, default "reminder"
            通知のシナリオ、
            "reminder", "alarm", "incomingCall", "urgent" が指定可能。
            "incomingCall" の場合、通知のタイムアウトが無効になる
        suppress_popup : bool, default False
            通知のポップアップを抑制するかどうか、
            `False` の場合、通知センターにのみ通知が表示される
        """
        notify(
            title = title,
            body = body,
            app_id = self._app_id,
            group = level.name,
            icon = self._app_icon_path[level] if self._app_icon_path else None,
            duration = duration,
            suppress_popup = suppress_popup,
            scenario = scenario
        )

    def clear_notifications(self):
        """トースト通知をクリアする

        以前の通知も含めて、本アプリケーションによる全てのトースト通知をクリアする"""
        clear_toast(self._app_id)
