import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('switch_engine', Path(__file__).parents[1] / 'src/antigravity_smart_switch.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
with tempfile.TemporaryDirectory() as directory:
    with patch.object(engine, 'LOCAL_APPDATA', directory):
        held = engine.AutoResumeLock(str(Path(directory) / 'Antigravity/private-proxy/account-switch.lock'))
        assert held.acquire()
        try:
            with patch.object(engine, '_run_smart_switch_locked') as run:
                assert engine.run_smart_switch(force=True) == 'busy'
                run.assert_not_called()
        finally:
            held.release()
        with patch.object(engine, '_run_smart_switch_locked', side_effect=RuntimeError('simulated')):
            try:
                engine.run_smart_switch()
            except RuntimeError:
                pass
        with patch.object(engine, '_run_smart_switch_locked', return_value='not_needed'):
            assert engine.run_smart_switch() == 'not_needed'
    log_path = Path(directory) / 'test.log'
    handler = engine.SharedRotatingFileHandler(log_path, maxBytes=1, backupCount=1, delay=True)
    with patch.object(engine.RotatingFileHandler, 'doRollover', side_effect=PermissionError('shared handle')):
        handler.doRollover()
        assert handler.stream is not None
    handler.close()
print('switch_coordination_ok')
