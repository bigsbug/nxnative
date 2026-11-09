"""Bedrock engine (.glslc) shader binary tests, without game data."""
import os
from pathlib import Path
import struct
import sys
import unittest

os.environ.setdefault('DM_GAME', '0100000000010000')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import shader_split as split


def bedrock_data(stage, reflection=b'TEST_REFLECTION'):
    ctl, code = bytearray(0x848), bytearray(0x100)
    ctl[:4] = split.CTL_MAGIC
    struct.pack_into('<I', ctl, 0x20, len(ctl))
    struct.pack_into('<I', ctl, 0x704, len(code))
    code[:4] = split.CS_MAGIC if stage == 'cs' else split.GFX_MAGIC
    if stage != 'cs':
        struct.pack_into('<I', code, 0x30, (split.STAGES.index(stage) + 1) << 10 | 1)
    blob = struct.pack('<I', len(code)) + code + struct.pack('<I', len(ctl)) + ctl + reflection
    return blob, bytes(ctl), bytes(code)


class BedrockShaderTests(unittest.TestCase):
    def test_stages_recognition(self):
        for stage in ('vs', 'ps', 'cs'):
            with self.subTest(stage=stage):
                data, ctl, code = bedrock_data(stage)
                found = []
                split.scan_blob(data, f'/{stage}.glslc', found)
                self.assertEqual(len(found), 1)
                self.assertEqual([(s, c, k) for _, s, c, k in found], [(stage, ctl, code)])
                self.assertIn('#BEDROCK', found[0][0])

    def test_single_stage_tuple(self):
        self.assertIn('#BEDROCK', split.SINGLE_STAGE)

    def test_truncated_or_unrelated_data_is_not_a_shader(self):
        data = bedrock_data('ps')[0]
        for bad in (data[:3], data[:8], data[:0x80], bytes(0x1000), struct.pack('<I', 0xffffffff) + data[4:]):
            with self.subTest(size=len(bad)):
                found = []
                split.scan_blob(bad, '/unrelated', found)
                self.assertEqual(found, [])

    def test_control_and_code_lengths_must_agree(self):
        data = bytearray(bedrock_data('vs')[0])
        # Corrupt ctl[0x704]
        ncode = struct.unpack_from('<I', data, 0)[0]
        ctloff = 8 + ncode
        struct.pack_into('<I', data, ctloff + 0x704, 0x80)
        with self.assertRaisesRegex(SystemExit, 'code area length'):
            split.scan_blob(bytes(data), '/bad_bedrock', [])


if __name__ == '__main__':
    unittest.main()
