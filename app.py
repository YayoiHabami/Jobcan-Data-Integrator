"""
アプリケーションのエントリーポイント
"""
import os
from jobcan_di.integrator.integrator import JobcanDataIntegrator, JobcanDIConfig

config = JobcanDIConfig(app_dir=os.path.join(os.getcwd(), "jobcan_di"))
with JobcanDataIntegrator(config) as di:
    pass# di.run()
