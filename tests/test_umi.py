import collections
import json
import os

import pytest

from archetypal import settings, get_eplus_dirs
from archetypal.umi_template import UmiTemplate


class TestUmiTemplate:
    """Test suite for the UmiTemplate class"""

    @pytest.mark.xfail(reason="There is still an issue with the order of the keys")
    def test_template_to_template(self, config):
        """load the json into UmiTemplate object, then convert back to json and
        compare"""
        import json

        file = "tests/input_data/umi_samples/BostonTemplateLibrary_2.json"

        a = UmiTemplate.read_file(file).to_json(
            settings.data_folder / "b.json", sort_keys=True, indent=False
        )
        b = TestUmiTemplate.read_json(file)
        assert a == json.dumps(b, sort_keys=True, indent=False)

    def test_umitemplate(self, config):
        """Test creating UmiTemplate from 2 IDF files"""
        idf_source = [
            "tests/input_data/necb/NECB 2011-FullServiceRestaurant-NECB HDD Method-CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw.idf",
            get_eplus_dirs(settings.ep_version)
            / "ExampleFiles"
            / "VentilationSimpleTest.idf",
        ]
        wf = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        a = UmiTemplate.read_idf(idf_source, wf, name="Mixed_Files")

        print(a.to_json())

    @pytest.mark.skipif(
        os.environ.get("CI", "False").lower() == "true",
        reason="not necessary to test this on CI",
    )
    def test_umi_samples(self, config):
        idf_source = [
            "tests/input_data/umi_samples/B_Off_0.idf",
            "tests/input_data/umi_samples/B_Ret_0.idf",
            "tests/input_data/umi_samples/B_Res_0_Masonry.idf",
            "tests/input_data/umi_samples/B_Res_0_WoodFrame.idf",
        ]
        wf = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        a = UmiTemplate.read_idf(idf_source, wf, name="Mixed_Files")

        print(a.to_json())

    @staticmethod
    def read_json(file):
        with open(file, "r") as f:
            a = json.load(f)
            data_dict = collections.OrderedDict(
                {
                    "GasMaterials": [],
                    "GlazingMaterials": [],
                    "OpaqueMaterials": [],
                    "OpaqueConstructions": [],
                    "WindowConstructions": [],
                    "StructureDefinitions": [],
                    "DaySchedules": [],
                    "WeekSchedules": [],
                    "YearSchedules": [],
                    "DomesticHotWaterSettings": [],
                    "VentilationSettings": [],
                    "ZoneConditionings": [],
                    "ZoneConstructionSets": [],
                    "ZoneLoads": [],
                    "Zones": [],
                    "WindowSettings": [],
                    "BuildingTemplates": [],
                }
            )
            data_dict.update(a)
            return data_dict
