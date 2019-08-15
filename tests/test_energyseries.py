import os

import archetypal as ar
import pandas as pd
import pytest

from path import Path


@pytest.fixture(scope="module")
def test_energydf(config):
    from archetypal import ReportData
    idfs = [
        "tests/input_data/regular/5ZoneNightVent1.idf",
        "tests/input_data/regular/AdultEducationCenter.idf",
    ]
    outputs = {
        "ep_object": "Output:Variable".upper(),
        "kwargs": {
            "Key_Value": "OCCUPY-1",
            "Variable_Name": "Schedule Value",
            "Reporting_Frequency": "Hourly",
        },
    }
    wf = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
    sql = {
        idf: ar.run_eplus(
            idf,
            weather_file=wf,
            prep_outputs=[outputs],
            annual=True,
            expandobjects=True,
            output_report="sql",
        )
        for idf in idfs
    }
    report = ar.get_from_reportdata(sql)

    ep = ar.reportdata.ReportData(report)
    sv = ep.filter_report_data(
        name=("Heating:Electricity", "Heating:Gas", "Heating:DistrictHeating")
    )
    hl = sv.heating_load(normalize=False, sort=False, concurrent_sort=False)

    yield hl


@pytest.fixture(params=["Water Heater Tank Temperature", "WaterSystems:EnergyTransfer"])
def rd(request):
    from archetypal import ReportData

    file = Path("tests/input_data/trnsys/HeatPumpWaterHeater.sqlite")

    rd = ReportData.from_sqlite(file, table_name=request.param)
    assert not rd.empty
    yield rd


def test_EnergySeries(rd):
    import matplotlib.pyplot as plt
    from archetypal import EnergySeries

    es = EnergySeries.from_sqlite(rd)
    es.plot()
    plt.show()
    print(es)


@pytest.mark.parametrize("kind", ["polygon", "surface"])
def test_plot_3d(test_energydf, kind):
    hl = test_energydf.copy()
    hl.plot3d(
        save=True,
        axis_off=True,
        kind=kind,
        cmap=None,
        fig_width=3,
        fig_height=8,
        edgecolors="k",
        linewidths=0.5,
    )


@pytest.mark.xfail(
    "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true",
    reason="Skipping this test on Travis CI.",
)
def test_plot_2d(test_energydf):
    hl = test_energydf.copy()
    hl = hl.unstack(level=0)
    hl.plot2d(
        save=False,
        axis_off=False,
        cmap="RdBu",
        subplots=True,
        fig_width=6,
        fig_height=6,
        edgecolors="k",
        linewidths=0.5,
    )


@pytest.fixture(scope="module")
def from_csv(config):
    file = "tests/input_data/test_profile.csv"
    df = pd.read_csv(file, index_col=[0], names=["Heat"])
    ep = ar.EnergySeries(
        df.Heat, units="BTU/hour", frequency="1H", to_units="kW", sort_values=False
    )
    # ep = ep.unit_conversion(to_units='kW')
    yield ep


@pytest.mark.xfail(
    "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true",
    reason="Skipping this test on Travis CI.",
)
def test_discretize(from_csv):
    epc = from_csv.copy()
    res = epc.discretize_tsam()
    res.plot()
    ar.plt.show()


def test_discretize_tsam(from_csv):
    ep = from_csv.copy()
    ldc_disc = ep.discretize_tsam(noTypicalPeriods=10)

    ldc_disc.plot2d(subplots=False)
