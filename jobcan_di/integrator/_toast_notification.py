"""
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
from typing import Optional

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
