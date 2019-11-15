Modules
=======

IDF Class
---------

.. currentmodule:: archetypal.idfclass

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    load_idf
    IDF
    run_eplus

.. _templates_label:

Template Classes
----------------

.. currentmodule:: archetypal.template

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    BuildingTemplate
    ZoneConditioning
    DomesticHotWaterSetting
    GasMaterial
    GlazingMaterial
    ZoneLoad
    OpaqueConstruction
    OpaqueMaterial
    UmiSchedule
    StructureDefinition
    VentilationSetting
    WindowConstruction
    WindowSetting
    Zone
    ZoneConstructionSet

Helper Classes
--------------

Classes that support the :ref:`templates_label` classes above.

.. currentmodule:: archetypal.template

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    Unique
    UmiBase
    MaterialBase
    MaterialLayer
    ConstructionBase
    LayeredConstruction
    MassRatio
    YearScheduleParts
    DaySchedule
    WeekSchedule
    YearSchedule
    WindowType

Graph Module
------------

.. currentmodule:: archetypal.template

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    ZoneGraph


Schedule Module
---------------

.. currentmodule:: archetypal.schedule

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    Schedule


Data Portal
-----------

.. currentmodule:: archetypal.dataportal

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    tabula_available_buildings
    tabula_api_request
    tabula_building_details_sheet
    tabula_system
    tabula_system_request
    openei_api_request
    nrel_api_cbr_request
    nrel_bcl_api_request
    stat_can_request
    stat_can_geo_request
    download_bld_window
    save_to_cache
    get_from_cache


EnergyDataFrame
---------------

.. currentmodule:: archetypal.energydataframe

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    set_unit
    discretize_tsam
    plot_energydataframe_map


EnergySeries
------------

.. currentmodule:: archetypal.energyseries

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    save_and_show
    plot_energyseries
    plot_energyseries_map