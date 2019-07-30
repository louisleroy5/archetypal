import functools
import logging as lg
import time

import numpy as np
import pandas as pd

from archetypal import log, EnergySeries


class ReportData(pd.DataFrame):
    """This class serves as a subclass of a pandas DataFrame allowing to add
    additional functionnality"""

    ARCHETYPE = 'Archetype'
    REPORTDATAINDEX = 'ReportDataIndex'
    TIMEINDEX = 'TimeIndex'
    REPORTDATADICTIONARYINDEX = 'ReportDataDictionaryIndex'
    VALUE = 'Value'
    ISMETER = 'IsMeter'
    TYPE = 'Type'
    INDEXGROUP = 'IndexGroup'
    TIMESTEPTYPE = 'TimestepType'
    KEYVALUE = 'KeyValue'
    NAME = 'Name'
    REPORTINGFREQUENCY = 'ReportingFrequency'
    SCHEDULENAME = 'ScheduleName'
    UNITS = 'Units'

    @classmethod
    def from_sql(cls, sql_dict):
        report_data = sql_dict['ReportData']
        report_data['ReportDataDictionaryIndex'] = pd.to_numeric(
            report_data['ReportDataDictionaryIndex'])

        report_data_dict = sql_dict['ReportDataDictionary']

        return cls(report_data.reset_index().join(report_data_dict,
                                              on=['ReportDataDictionaryIndex']))

    @property
    def _constructor(self):
        return ReportData

    @property
    def schedules(self):
        return self.sorted_values(key_value='Schedule Value')

    @property
    def df(self):
        """Returns the DataFrame of the ReportData"""
        return pd.DataFrame(self)

    def heating_load(self, normalize=False, sort=False, ascending=False,
                     concurrent_sort=False):
        """Returns the aggragated 'Heating:Electricity', 'Heating:Gas' and
        'Heating:DistrictHeating' of each archetype

        Args:
            normalize (bool): if True, returns a normalize Series.
                Normalization is done with respect to each Archetype
            sort (bool): if True, sorts the values. Usefull when a load
                duration curve is needed.
            ascending (bool): if True, sorts value in ascending order. If a
                Load Duration Curve is needed, use ascending=False.

        Returns:
            EnergySeries: the Value series of the Heating Load with a Archetype,
                TimeIndex as MultiIndex.
        """
        hl = self.filter_report_data(name=('Heating:Electricity',
                                           'Heating:Gas',
                                           'Heating:DistrictHeating'))
        freq = list(set(hl.ReportingFrequency))
        units = list(set(hl.Units))
        freq_map = dict(Hourly='H', Daily='D', Monthly='M')
        if len(units) > 1:
            raise MixedUnitsError()

        hl = hl.groupby(['Archetype', 'TimeIndex']).Value.sum()
        log('Returned Heating Load in units of {}'.format(str(units)),
            lg.DEBUG)
        return EnergySeries(hl, frequency=freq_map[freq[0]], units=units[0],
                            normalize=normalize, is_sorted=sort,
                            ascending=ascending, to_units='kWh',
                            concurrent_sort=concurrent_sort)

    def filter_report_data(self, archetype=None, reportdataindex=None,
                           timeindex=None, reportdatadictionaryindex=None,
                           value=None, ismeter=None, type=None,
                           indexgroup=None, timesteptype=None, keyvalue=None,
                           name=None, reportingfrequency=None,
                           schedulename=None, units=None, inplace=False):
        """filter RaportData using specific keywords. Each keywords can be a
        tuple of strings (str1, str2, str3) which will return the logical_or
        on the specific column.

        Args:
            archetype (str or tuple):
            reportdataindex (str or tuple):
            timeindex (str or tuple):
            reportdatadictionaryindex (str or tuple):
            value (str or tuple):
            ismeter (str or tuple):
            type (str or tuple):
            indexgroup (str or tuple):
            timesteptype (str or tuple):
            keyvalue (str or tuple):
            name (str or tuple):
            reportingfrequency (str or tuple):
            schedulename (str or tuple):
            units (str or tuple):
            inplace (str or tuple):

        Returns:
            pandas.DataFrame
        """
        start_time = time.time()
        c_n = []

        if archetype:
            c_1 = conjunction(*[self[self.ARCHETYPE] ==
                                archetype for
                                archetype in
                                archetype], logical=np.logical_or) \
                if isinstance(archetype, tuple) \
                else self[self.ARCHETYPE] == archetype
            c_n.append(c_1)
        if reportdataindex:
            c_2 = conjunction(*[self[self.REPORTDATAINDEX] ==
                                reportdataindex for
                                reportdataindex in
                                reportdataindex],
                              logical=np.logical_or) \
                if isinstance(reportdataindex, tuple) \
                else self[self.REPORTDATAINDEX] == reportdataindex
            c_n.append(c_2)
        if timeindex:
            c_3 = conjunction(*[self[self.TIMEINDEX] ==
                                timeindex for
                                timeindex in
                                timeindex],
                              logical=np.logical_or) \
                if isinstance(timeindex, tuple) \
                else self[self.TIMEINDEX] == timeindex
            c_n.append(c_3)
        if reportdatadictionaryindex:
            c_4 = conjunction(*[self[self.REPORTDATADICTIONARYINDEX] ==
                                reportdatadictionaryindex for
                                reportdatadictionaryindex in
                                reportdatadictionaryindex],
                              logical=np.logical_or) \
                if isinstance(reportdatadictionaryindex, tuple) \
                else self[self.REPORTDATADICTIONARYINDEX] == \
                     reportdatadictionaryindex
            c_n.append(c_4)
        if value:
            c_5 = conjunction(*[self[self.VALUE] ==
                                value for
                                value in
                                value], logical=np.logical_or) \
                if isinstance(value, tuple) \
                else self[self.VALUE] == value
            c_n.append(c_5)
        if ismeter:
            c_6 = conjunction(*[self[self.ISMETER] ==
                                ismeter for
                                ismeter in
                                ismeter],
                              logical=np.logical_or) \
                if isinstance(ismeter, tuple) \
                else self[self.ISMETER] == ismeter
            c_n.append(c_6)
        if type:
            c_7 = conjunction(*[self[self.TYPE] ==
                                type for
                                type in
                                type],
                              logical=np.logical_or) \
                if isinstance(type, tuple) \
                else self[self.TYPE] == type
            c_n.append(c_7)
        if indexgroup:
            c_8 = conjunction(*[self[self.INDEXGROUP] ==
                                indexgroup for
                                indexgroup in
                                indexgroup],
                              logical=np.logical_or) \
                if isinstance(indexgroup, tuple) \
                else self[self.INDEXGROUP] == indexgroup
            c_n.append(c_8)
        if timesteptype:
            c_9 = conjunction(*[self[self.TIMESTEPTYPE] ==
                                timesteptype for
                                timesteptype in
                                timesteptype],
                              logical=np.logical_or) \
                if isinstance(timesteptype, tuple) \
                else self[self.TIMESTEPTYPE] == timesteptype
            c_n.append(c_9)
        if keyvalue:
            c_10 = conjunction(*[self[self.KEYVALUE] ==
                                 keyvalue for
                                 keyvalue in
                                 keyvalue],
                               logical=np.logical_or) \
                if isinstance(keyvalue, tuple) \
                else self[self.KEYVALUE] == keyvalue
            c_n.append(c_10)
        if name:
            c_11 = conjunction(*[self[self.NAME] ==
                                 name for
                                 name in
                                 name],
                               logical=np.logical_or) \
                if isinstance(name, tuple) \
                else self[self.NAME] == name
            c_n.append(c_11)
        if reportingfrequency:
            c_12 = conjunction(*[self[self.REPORTINGFREQUENCY] ==
                                 reportingfrequency for
                                 reportingfrequency in
                                 reportingfrequency],
                               logical=np.logical_or) \
                if isinstance(reportingfrequency, tuple) \
                else self[self.REPORTINGFREQUENCY] == reportingfrequency
            c_n.append(c_12)
        if schedulename:
            c_13 = conjunction(*[self[self.SCHEDULENAME] ==
                                 schedulename for
                                 schedulename in
                                 schedulename],
                               logical=np.logical_or) \
                if isinstance(schedulename, tuple) \
                else self[self.SCHEDULENAME] == schedulename
            c_n.append(c_13)
        if units:
            c_14 = conjunction(*[self[self.UNITS] ==
                                 units for
                                 units in
                                 units], logical=np.logical_or) \
                if isinstance(units, tuple) \
                else self[self.UNITS] == units
            c_n.append(c_14)

        filtered_df = self.loc[conjunction(*c_n, logical=np.logical_and)]
        log('filtered ReportData in {:,.2f} seconds'.format(
            time.time() - start_time))
        if inplace:
            return filtered_df._update_inplace(filtered_df)
        else:
            return filtered_df.__finalize__(self)

    def sorted_values(self, key_value=None, name=None,
                      by='TimeIndex', ascending=True):
        """Returns sorted values by filtering key_value and name

        Args:
            self: The ReporatData DataFrame
            key_value (str): key_value column filter
            name (str): name column filter
            by (str): sorting by this column name
            ascending (bool):

        Returns:
            ReportData
        """
        if key_value and name:
            return self.filter_report_data(name=name,
                                           keyvalue=key_value).sort_values(
                by=by, ascending=ascending).reset_index(drop=True).rename_axis(
                'TimeStep').set_index([
                'Archetype'], append=True).swaplevel(i=-2, j=-1, axis=0)
        else:
            return self.sort_values(by=by, inplace=False)


def conjunction(*conditions, logical=np.logical_and):
    """Applies a logical function on n conditons"""
    return functools.reduce(logical, conditions)


def or_conjunction(*conditions):
    return functools.reduce(np.logical_or, conditions)