"""测试包：共享一个临时数据库，避免污染项目数据"""

import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="phonetics-tests-")
os.environ["DB_PATH"] = os.path.join(_TEST_DIR, "phonetics-test.db")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
