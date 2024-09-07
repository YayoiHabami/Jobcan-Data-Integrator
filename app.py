"""
アプリケーションのエントリーポイント
"""
import datetime
import os
import time

from jobcan_di.integrator.integrator import JobcanDataIntegrator, JobcanDIConfig
from jobcan_di.status.errors import RequestConnectionError, RequestReadTimeout



def main() -> None:
    """
    アプリケーションのエントリーポイント
    """
    # Requestに失敗した場合のリトライ間隔 (秒)
    sleep_sec = [60, 60*5, 60*15]

    config = JobcanDIConfig(app_dir=os.path.join(os.getcwd(), "jobcan_di"))
    with JobcanDataIntegrator(config) as di:
        err = di.run()
        while err is not None:
            # エラーによる終了
            if isinstance(err, RequestConnectionError) or isinstance(err, RequestReadTimeout):
                if not sleep_sec:
                    print("Retry limit exceeded.")
                    break
                until_dt = datetime.datetime.now() + datetime.timedelta(seconds=sleep_sec[0])
                print(f"waiting {sleep_sec[0]} sec... (until {until_dt.strftime('%H:%M:%S')})")
                time.sleep(sleep_sec.pop(0))

            err = di.restart()



if __name__ == "__main__":
    main()
