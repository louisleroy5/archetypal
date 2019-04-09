import logging as lg

import pandas as pd
from archetypal import log


class Schedule(object):
    """An object designed to handle any EnergyPlys schedule object"""

    def __init__(self, idf, sch_name, start_day_of_the_week=0):
        self.idf = idf
        # self.hb_EPObjectsAUX = sc.sticky["honeybee_EPObjectsAUX"]()
        # self.lb_preparation = sc.sticky["ladybug_Preparation"]()
        self.schName = sch_name
        self.startDayOfTheWeek = start_day_of_the_week
        self.count = 0
        self.startHOY = 1
        self.endHOY = 24
        self.unit = "unknown"

    @property
    def all_values(self):
        return self.get_schedule_values(self.schName)

    def get_schedule_type_limits_data(self, sch_name):
        """Returns Scehdule Type Limits data"""

        if sch_name is None:
            sch_name = self.schName

        schedule = self.idf.get_schedule_type_limits_data_by_name(sch_name)
        try:
            lower_limit, upper_limit, numeric_type, unit_type = schedule.obj[2:]
        except:
            lower_limit, upper_limit, numeric_type = schedule.obj[2:]
            unit_type = "unknown"

        self.unit = unit_type
        if self.unit == "unknown":
            self.unit = numeric_type

        return lower_limit, upper_limit, numeric_type, unit_type

    def get_interval_day_ep_schedule_values(self, sch_name=None):
        """'Schedule:Day:Interval"""

        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())
        type_limit_name = values.Schedule_Type_Limits_Name
        lower_limit, upper_limit, numeric_type, unit_type = \
            self.get_schedule_type_limits_data(type_limit_name)

        number_of_day_sch = int((len(values) - 3) / 2)

        hourly_values = list(range(24))
        start_hour = 0
        for i in range(number_of_day_sch):
            value = float(values['Value_Until_Time_{}'.format(i + 1)])
            until_time = [int(s.strip()) for s in
                          values['Time_{}'.format(i + 1)].split(":") if
                          s.strip().isdigit()]
            end_hour = int(until_time[0] + until_time[1] / 60)
            for hour in range(start_hour, end_hour):
                hourly_values[hour] = value

            start_hour = end_hour

        if numeric_type.strip().lower() == "discrete":
            hourly_values = list(map(int, hourly_values))

        return hourly_values

    def get_hourly_day_ep_schedule_values(self, sch_name=None):
        """'Schedule:Day:Hourly'"""
        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())

        return values.fieldvalues[3:]

    def get_compact_weekly_ep_schedule_values(self, sch_name=None):
        """'schedule:week:compact'"""
        # Todo: get_compact_weekly_ep_schedule_values

        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())

        return []

    def get_daily_weekly_ep_schedule_values(self, sch_name=None):
        """'schedule:week:daily'"""
        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())

        # 7 list for 7 days of the week
        hourly_values_for_the_week = []
        for day_schedule in values.fieldvalues[2:9]:
            hourly_values_for_the_week.extend(
                self.get_schedule_values(day_schedule))

        return hourly_values_for_the_week

    def get_list_day_ep_schedule_values(self, sch_name=None):
        """'schedule:day:list'"""
        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())

        import pandas as pd
        freq = int(values['Minutes_per_Item'])  # Frequency of the values
        num_values = values.fieldvalues[5:]  # List of values
        method = values['Interpolate_to_Timestep']  # How to resample

        # fill a list of availbale values and pad with zeros (this is safer
        # but should not occur)
        all_values = list(range(int(24 * 60 / freq)))
        for i in all_values:
            try:
                all_values[i] = num_values[i]
            except:
                all_values[i] = 0
        # create a fake index to help us with the resampling
        index = pd.date_range(start='1/1/2018',
                              periods=(24 * 60) / freq,
                              freq='{}T'.format(freq))
        series = pd.Series(all_values, index=index)

        # resample series to hourly values and apply resampler function
        series = series.resample('1H').apply(how(method))

        return series.to_list()

    def get_constant_ep_schedule_values(self, sch_name=None):
        """'schedule:constant'"""
        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())

        type_limit_name = values.Schedule_Type_Limits_Name
        lower_limit, upper_limit, numeric_type, unit_type = \
            self.get_schedule_type_limits_data(type_limit_name)
        hourly_values = list(range(8760))
        value = float(values['Hourly_Value'])
        for hour in hourly_values:
            hourly_values[hour] = value

        if numeric_type.strip().lower() == 'discrete':
            hourly_values = list(map(int, hourly_values))

        return hourly_values

    def get_file_ep_schedule_values(self, sch_name=None):
        """'schedule:file'"""
        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())
        filename = values['File_Name']
        column = values['Column_Number']
        rows = values['Rows_to_Skip_at_Top']
        hours = values['Number_of_Hours_of_Data']
        sep = values['Column_Separator']
        interp = values['Interpolate_to_Timestep']

        import pandas as pd
        import os
        idfdir = os.path.dirname(self.idf.idfname)
        file = os.path.join(idfdir, filename)
        delimeter = separator(sep)
        skip_rows = int(rows) - 1  # We want to keep the column
        col = [int(column)]
        values = pd.read_csv(file, delimiter=delimeter, skiprows=skip_rows,
                             usecols=col)

        return values.iloc[:, 0].to_list()

    def get_compact_ep_schedule_values(self, sch_name=None):
        """'schedule:compact'"""
        # Todo: get_compact_ep_schedule_values
        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())
        field_sets = ['through', 'for', 'interpolate', 'until', 'value']
        fields = values.fieldvalues[3:]
        import pandas as pd
        import numpy as np
        index = pd.date_range(start='2018/1/1', periods=8760, freq='1H')
        zeros = np.zeros(8760)

        series = pd.Series(zeros, index=index)
        from datetime import datetime, timedelta
        from_day = datetime.strptime('2018/01/01', '%Y/%m/%d')
        from_time = '00:00'
        for field in fields:
            if any([spe in field.lower() for spe in field_sets]):
                # we are dealing with a Field-Set (Through, For, Interpolate,
                # Until, Value)
                try:
                    # the colon (:) after these elements (Through, For,
                    # Until) is optional. We can catch this behaviour with a
                    # try, except statement
                    f_set, value = field.split(':')
                    value = value.strip()  # remove trailing spaces
                except:
                    # The field does not have a colon or has more than one!
                    try:
                        # The field has more than one colon
                        f_set, hour, minute = field.split(':')
                        hour = hour.strip()  # remove trailing spaces
                        minute = minute.strip()
                    except:
                        # The field does not have a colon. Simply capitalize
                        # and use value
                        f_set = spe.capitalize()
                        value = field[len(spe) + 1:].strip()

                if f_set.lower() == 'through':
                    # main condition. All sub-conditions must obey a
                    # `Through` condition

                    # First, initialize the slice (all False for now)
                    all_conditions = series.apply(lambda x: False)

                    # reset from_time
                    from_time = '00:00'

                    # Prepare to_day variable
                    to_day = datetime.strptime('2018/' + value, '%Y/%m/%d')

                    # Add one hour because EP is 24H based while pandas is
                    # 0-based eg.: 00:00 to 23:59 versus 01:01 to 24:00
                    to_day = to_day + timedelta(days=1)

                    # slice the conditions with the range and apply True
                    all_conditions.loc[from_day:to_day] = True

                    # update in memory slice. In case `For: AllOtherDays` is
                    # used in another Field
                    sliced_day.loc[from_day:to_day] = True

                    # add one day to from_day in preparation for the next
                    # Through condition.
                    from_day = to_day + timedelta(days=1)
                elif f_set.lower() == 'for':
                    # slice specific days

                    for_condition = series.apply(lambda x: False)
                    values = value.split()
                    if len(values) > 1:
                        # if multiple `For`. eg.: For: Weekends Holidays,
                        # Combine both conditions
                        for value in values:
                            how = field_set(value)
                            for_condition.loc[how] = True
                    else:
                        # Apply condition to slice
                        how = field_set(value)
                        for_condition.loc[how] = True

                    # Combine the for_condition with all_conditions
                    all_conditions = all_conditions & for_condition

                    # update in memory slice
                    sliced_day.loc[all_conditions] = True
                elif f_set.lower() == 'interpolate':
                    raise NotImplementedError('Archetypal does not support '
                                              '"interpolate" statements yet')
                elif f_set.lower() == 'until':
                    for_condition = series.apply(lambda x: False)
                    until_time = str(int(hour) - 1) + ':' + minute
                    for_condition.loc[for_condition.between_time(from_time,
                                                                 until_time).index] = True
                    all_conditions = for_condition & all_conditions

                    # update in memory slice
                    sliced_day.loc[all_conditions] = True

                    from_time = until_time
                elif f_set.lower() == 'value':
                    # If the therm `Value: ` field is used, we will catch it
                    # here.
                    series[all_conditions] = value
                else:
                    pass
            else:
                # If the term `Value: ` is not used; the variable is simply
                # passed in the Field
                value = float(field)
                series[all_conditions] = value

        return series.to_list()

    def get_yearly_ep_schedule_values(self, sch_name=None):
        """'schedule:year'"""
        # place holder for 365 days
        hourly_values = range(365)

        # update last day of schedule
        self.endHOY = 8760

        if sch_name is None:
            sch_name = self.schName

        values = self.idf.get_schedule_data_by_name(sch_name.upper())

        # generate weekly schedules
        num_of_weekly_schedules = int(len(values) / 5)

        for i in range(num_of_weekly_schedules):
            week_day_schedule_name = values[
                'ScheduleWeek_Name_{}'.format(i + 1)]

            start_day = values['Start_Day_{}'.format(i + 1)]
            end_day = values['End_Day_{}'.format(i + 1)]

            # 7 list for 7 days of the week
            hourly_values_for_the_week = self.get_schedule_values(
                week_day_schedule_name)

            for day in range(start_day - 1, end_day):
                hourly_values[day] = hourly_values_for_the_week[day % 7]

        return hourly_values

    def get_schedule_values(self, sch_name=None):
        """Main function that returns the schedule values"""
        if sch_name is None:
            sch_name = self.schName
        if self.is_schedule(sch_name):
            schedule_values = self.idf.get_schedule_data_by_name(
                sch_name.upper())

            schedule_type = schedule_values.fieldvalues[0].upper()
            if self.count == 0:
                self.schType = schedule_type

            self.count += 1

            if schedule_type == "schedule:year".upper():
                hourly_values = self.get_yearly_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:day:interval".upper():
                hourly_values = self.get_interval_day_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:day:hourly".upper():
                hourly_values = self.get_hourly_day_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:day:list".upper():
                hourly_values = self.get_list_day_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:week:compact".upper():
                hourly_values = self.get_compact_weekly_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:week:daily".upper():
                hourly_values = self.get_daily_weekly_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:constant".upper():
                hourly_values = self.get_constant_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:compact".upper():
                hourly_values = self.get_compact_ep_schedule_values(
                    sch_name)
            elif schedule_type == "schedule:file".upper():
                hourly_values = self.get_file_ep_schedule_values(
                    sch_name)
            else:
                log('Archetypal does not support "{}" currently'.format(
                    schedule_type), lg.WARNING)

                hourly_values = []

            return hourly_values

    def is_schedule(self, sch_name):
        """Returns True if idfobject is one of 'schedule_types'"""
        for obj in self.idf.idfobjects:
            for bunch in self.idf.idfobjects[obj]:
                try:
                    if bunch.Name.upper() == sch_name.upper():
                        obj_type = bunch.fieldvalues[0]
                        if obj_type.upper() in schedule_types:
                            return True
                        else:
                            return False
                except:
                    pass


def separator(sep):
    """helper function to return the correct delimiter"""
    if sep == 'Comma':
        return ','
    elif sep == 'Tab':
        return '\t'
    elif sep == 'Fixed':
        return None
    elif sep == 'Semicolon':
        return ';'
    else:
        return None


def how(how):
    """Helper function to return the correct resampler"""
    if how.lower() == 'average':
        return 'mean'
    elif how.lower() == 'linear':
        return 'interpolate'
    elif how.lower() == 'no':
        return 'max'
    else:
        return 'max'


def field_set(field):
    """helper function to return the proper slicer depending on the field_set

    Weekdays, Weekends, Holidays, Alldays, SummerDesignDay, WinterDesignDay,
     Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday,
     CustomDay1, CustomDay2, AllOtherDays"""

    if field.lower() == 'weekdays':
        # return only days of weeks
        return lambda x: x.index.dayofweek < 5
    elif field.lower() == 'weekends':
        # return only weekends
        return lambda x: x.index.dayofweek >= 5
    elif field.lower() == 'alldays':
        # return all days := equivalenet to .loc[:]
        return pd.IndexSlice[:]
    elif field.lower() == 'allotherdays':
        # return unused days. Uses the global variable `sliced_day`
        return ~sliced_day
    elif field.lower() == 'sunday':
        # return only sundays
        return lambda x: x.index.dayofweek == 6
    elif field.lower() == 'monday':
        # return only mondays
        return lambda x: x.index.dayofweek == 0
    elif field.lower() == 'tuesday':
        # return only Tuesdays
        return lambda x: x.index.dayofweek == 1
    elif field.lower() == 'wednesday':
        # return only Wednesdays
        return lambda x: x.index.dayofweek == 2
    elif field.lower() == 'thursday':
        # return only Thursdays
        return lambda x: x.index.dayofweek == 3
    elif field.lower() == 'friday':
        # return only Fridays
        return lambda x: x.index.dayofweek == 4
    elif field.lower() == 'saturday':
        # return only Saturdays
        return lambda x: x.index.dayofweek == 5
    else:
        raise NotImplementedError('Archetypal does not yet support The '
                                  'Field_set "{}"'.format(field))


index = pd.date_range(start='2018/1/1', periods=8760, freq='1H')
sliced_day = pd.Series(range(8760), index=index).apply(lambda x: False)

schedule_types = ['Schedule:Day:Hourly'.upper(),
                  'Schedule:Day:Interval'.upper(), 'Schedule:Day:List'.upper(),
                  'Schedule:Week:Daily'.upper(), 'Schedule:Year'.upper(),
                  'Schedule:Week:Compact'.upper(), 'Schedule:Compact'.upper(),
                  'Schedule:Constant'.upper(), 'Schedule:File'.upper()]
