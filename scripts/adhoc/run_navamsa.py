import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, 'sbc')

from sbc.navamsa_pipeline.cli import main
if __name__ == "__main__":
    main()
