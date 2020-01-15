################################################################################
# Module: cli.py
# Description: Implements archetypal functions as Command Line Interfaces
# License: MIT, see full license in LICENSE.txt
# Web: https://github.com/samuelduchesne/archetypal
################################################################################
import os
import time
from collections import defaultdict
from typing import Any, Union

from path import Path

import click

from archetypal import (
    settings,
    cd,
    load_idf,
    convert_idf_to_trnbuild,
    get_eplus_dirs,
    parallel_process,
    run_eplus,
    IDF,
    UmiTemplate,
    config,
    log,
    idf_version_updater,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class CliConfig(object):
    def __init__(self):
        self.data_folder = settings.data_folder
        self.logs_folder = settings.logs_folder
        self.imgs_folder = settings.imgs_folder
        self.cache_folder = settings.cache_folder
        self.use_cache = settings.use_cache
        self.log_file = settings.log_file
        self.log_console = settings.log_console
        self.log_level = settings.log_level
        self.log_name = settings.log_name
        self.log_filename = settings.log_filename
        self.useful_idf_objects = settings.useful_idf_objects
        self.umitemplate = settings.umitemplate
        self.trnsys_default_folder = settings.trnsys_default_folder
        self.ep_version = settings.ep_version


pass_config = click.make_pass_decorator(CliConfig, ensure=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--data-folder",
    type=click.Path(),
    help="where to save and load data files",
    default=settings.data_folder,
)
@click.option(
    "--logs-folder",
    type=click.Path(),
    help="where to write the log files",
    default=settings.logs_folder,
)
@click.option(
    "--imgs-folder",
    type=click.Path(),
    help="where to save figures",
    default=settings.imgs_folder,
)
@click.option(
    "--cache-folder",
    type=click.Path(),
    help="where to save the simluation results",
    default=settings.cache_folder,
)
@click.option(
    "-c/-nc",
    "--use-cache/--no-cache",
    help="Use a local cache to save/retrieve many of "
    "archetypal outputs such as EnergyPlus simulation results",
    default=True,
)
@click.option(
    "-l",
    "--log-file",
    is_flag=True,
    help="save log output to a log file in logs_folder",
    default=settings.log_file,
)
@click.option(
    "--verbose/--noverbose",
    "-v/-nv",
    "log_console",
    default=True,
    help="print log output to the console",
)
@click.option(
    "--log-level",
    type=click.INT,
    help="CRITICAL=50, ERROR=40, WARNING=30, INFO=20, DEBUG=10",
    default=settings.log_level,
)
@click.option("--log-name", help="name of the logger", default=settings.log_name)
@click.option(
    "--log-filename", help="name of the log file", default=settings.log_filename
)
@click.option(
    "--trnsys-default-folder",
    type=click.Path(),
    help="root folder of TRNSYS install",
    default=settings.trnsys_default_folder,
)
@click.option(
    "--ep_version",
    type=click.STRING,
    default=settings.ep_version,
    help='the EnergyPlus version to use. eg. "{}"'.format(settings.ep_version),
)
@pass_config
def cli(
    cli_config,
    data_folder,
    logs_folder,
    imgs_folder,
    cache_folder,
    use_cache,
    log_file,
    log_console,
    log_level,
    log_name,
    log_filename,
    trnsys_default_folder,
    ep_version,
):
    """archetypal: Retrieve, construct, simulate, convert and analyse building
    simulation templates

    Visit archetypal.readthedocs.io for the online documentation.
    """
    cli_config.data_folder = data_folder
    cli_config.logs_folder = logs_folder
    cli_config.imgs_folder = imgs_folder
    cli_config.cache_folder = cache_folder
    cli_config.use_cache = use_cache
    cli_config.log_file = log_file
    cli_config.log_console = log_console
    cli_config.log_level = log_level
    cli_config.log_name = log_name
    cli_config.log_filename = log_filename
    cli_config.trnsys_default_folder = trnsys_default_folder
    cli_config.ep_version = ep_version
    # apply new config params
    config(**cli_config.__dict__)


@cli.command()
@click.argument("idf-file", type=click.Path(exists=True))
@click.argument(
    "output-folder", type=click.Path(exists=True), required=False, default="."
)
@click.option(
    "--return-idf",
    "-i",
    is_flag=True,
    default=False,
    help="Save modified IDF file to output_folder, and return path "
    "to the file in the console",
)
@click.option(
    "--return_t3d",
    "-t",
    is_flag=True,
    default=False,
    help="Return T3D file path in the console",
)
@click.option(
    "--return_dck",
    "-d",
    is_flag=True,
    default=False,
    help="Generate dck file and save to output_folder, and return "
    "path to the file in the console",
)
@click.option(
    "--window-lib",
    type=click.Path(),
    default=None,
    help="Path of the window library (from Berkeley Lab)",
)
@click.option(
    "--trnsidf-exe",
    type=click.Path(),
    help="Path to trnsidf.exe",
    default=os.path.join(
        settings.trnsys_default_folder, r"Building\trnsIDF\trnsidf.exe"
    ),
)
@click.option(
    "--template",
    type=click.Path(),
    default=settings.path_template_d18,
    help="Path to d18 template file",
)
@click.option(
    "--log-clear-names",
    is_flag=True,
    default=False,
    help='Do not print log of "clear_names" (equivalence between '
    "old and new names) in the console",
)
@click.option(
    "--window",
    nargs=4,
    type=float,
    default=(2.2, 0.64, 0.8, 0.05),
    help="Specify window properties <u_value> <shgc> <t_vis> "
    "<tolerance>. Default = 2.2 0.64 0.8 0.05",
)
@click.option("--ordered", is_flag=True, help="sort idf object names")
@click.option("--nonum", is_flag=True, default=False, help="Do not renumber surfaces")
@click.option("--batchjob", "-N", is_flag=True, default=False, help="BatchJob Modus")
@click.option(
    "--geofloor",
    type=float,
    default=0.6,
    help="Generates GEOSURF values for distributing; direct solar "
    "radiation where `geo_floor` % is directed to the floor, "
    "the rest; to walls/windows. Default = 0.6",
)
@click.option(
    "--refarea",
    is_flag=True,
    default=False,
    help="Upadtes floor reference area of airnodes",
)
@click.option(
    "--volume", is_flag=True, default=False, help="Upadtes volume of airnodes"
)
@click.option(
    "--capacitance", is_flag=True, default=False, help="Upadtes capacitance of airnodes"
)
def convert(
    idf_file,
    window_lib,
    return_idf,
    return_t3d,
    return_dck,
    output_folder,
    trnsidf_exe,
    template,
    log_clear_names,
    window,
    ordered,
    nonum,
    batchjob,
    geofloor,
    refarea,
    volume,
    capacitance,
):
    """Convert regular IDF file (EnergyPlus) to TRNBuild file (TRNSYS) The
    output folder path defaults to the working directory. Equivalent to '.'
    """
    u_value, shgc, t_vis, tolerance = window
    window_kwds = {
        "u_value": u_value,
        "shgc": shgc,
        "t_vis": t_vis,
        "tolerance": tolerance,
    }
    with cd(output_folder):
        paths = convert_idf_to_trnbuild(
            idf_file,
            window_lib,
            return_idf,
            True,
            return_t3d,
            return_dck,
            output_folder,
            trnsidf_exe,
            template,
            log_clear_names=log_clear_names,
            **window_kwds,
            ordered=ordered,
            nonum=nonum,
            N=batchjob,
            geo_floor=geofloor,
            refarea=refarea,
            volume=volume,
            capacitance=capacitance
        )
    # Print path of output files in console
    if paths:
        click.echo("Here are the paths to the different output files: ")

        for path in paths:
            if "MODIFIED" in path:
                click.echo("Path to the modified IDF file: {}".format(path))
            elif "b18" in path:
                click.echo("Path to the BUI file: {}".format(path))
            elif "dck" in path:
                click.echo("Path to the DCK file: {}".format(path))
            else:
                click.echo("Path to the T3D file: {}".format(path))


@cli.command()
@click.argument("idf", nargs=-1)
@click.argument("output", type=click.Path(), default="myumitemplate.json")
@click.option(
    "--weather",
    "-w",
    type=click.Path(exists=True),
    help="EPW weather file path",
    default=get_eplus_dirs(settings.ep_version)
    / "WeatherData"
    / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
    show_default=True,
)
@click.option(
    "-p",
    "parallel",
    is_flag=True,
    default=True,
    help="Parallel process; each idf file on different cores",
)
@click.option(
    "-z",
    "all_zones",
    is_flag=True,
    default=False,
    help="Include all zones in the " "output template",
)
def reduce(idf, output, weather, parallel, all_zones):
    """Perform the model reduction and translate to an UMI template file.
    """
    if parallel:
        # if parallel is True, run eplus in parallel
        rundict = {
            file: dict(
                eplus_file=file,
                weather_file=weather,
                annual=True,
                prep_outputs=True,
                expandobjects=True,
                verbose="v",
                output_report="sql",
                return_idf=False,
                ep_version=settings.ep_version,
            )
            for file in idf
        }
        res = parallel_process(rundict, run_eplus)
        loaded_idf = {}
        for key, sql in res.items():
            loaded_idf[key] = {}
            loaded_idf[key][0] = sql
            loaded_idf[key][1] = load_idf(key)
        res = loaded_idf
    else:
        # else, run sequentially
        res = defaultdict(dict)
        for fn in idf:
            res[fn][0], res[fn][1] = run_eplus(
                fn,
                weather,
                ep_version=settings.ep_version,
                output_report="sql",
                prep_outputs=True,
                annual=True,
                design_day=False,
                verbose="v",
                return_idf=True,
            )
    from archetypal import BuildingTemplate

    bts = []
    for fn in res.values():
        sql = next(
            iter([value for key, value in fn.items() if isinstance(value, dict)])
        )
        idf = next(iter([value for key, value in fn.items() if isinstance(value, IDF)]))
        bts.append(BuildingTemplate.from_idf(idf, sql=sql, DataSource=idf.name))

    output = Path(output)
    name = output.namebase
    ext = output.ext if output.ext == ".json" else ".json"
    dir_ = output.dirname()
    template = UmiTemplate(name=name, BuildingTemplates=bts)
    final_path: Path = dir_ / name + ext
    template.to_json(path_or_buf=final_path, all_zones=all_zones)
    log("Successfully created template file at {}".format(final_path.abspath()))


@cli.command()
@click.argument("idf", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-v",
    "--version",
    "to_version",
    default=settings.ep_version,
    help="EnergyPlus version to upgrade to - e.g., '9-2-0'",
)
@click.option(
    "-p",
    "--parallel",
    "cores",
    default=-1,
    help="Specify number of cores to run in parallel"
)
def transition(idf, to_version, cores):
    """Upgrade an IDF file to a newer version"""
    start_time = time.time()
    rundict = {
        idf: dict(
            idf_file=idf,
            to_version=to_version,
        )
        for idf in idf
    }
    parallel_process(rundict, idf_version_updater, processors=cores)
    log(
        "Successfully transitioned files to version '{}' in {:,.2f} seconds".format(
            to_version, time.time() - start_time
        )
    )
