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


Data Portals
------------

.. currentmodule:: archetypal.dataportal

.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    tabula_available_buildings
    tabula_building_details_sheet
    download_bld_window