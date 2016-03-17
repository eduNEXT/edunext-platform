#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import logging
from pprint import pformat as pf

logger = logging.getLogger(__name__)


class XmlDumpParser(object):
    """
    Xml dump file parser. Iterates over the dump and returns as dicts the information needed.
    """

    def __init__(self, filename):
        """Init the parser for the dump file.

        Args:
            filename (str): File name with its location e.g. "/var/tmp/dump.xml"
        """
        tree = ET.parse(filename)
        root = tree.getroot()
        self.database = root[0]

    def process_table(self, table_name):
        """Search through the xml for a table with 'table_name'. Returns list of dicts.
        Args:
            table_name (str):
        Returns:
            List of dicts: Each dict is a row of the table.
        """
        for table in self.database.findall("table_data[@name='{0}']".format(table_name)):
            table_list_dic = []
            for row in table.findall('row'):
                row_dic = {}
                for field in row.findall('field'):
                    row_dic[field.get('name')] = field.text
                table_list_dic.append(row_dic)
        return table_list_dic

    def process_join(self, table_joiner, left_join=False):
        """Search through the xml and join the tables specified by table_joiner. Return list of dicts.
        Args:
            table_joiner (TableJoiner)
            left_join (bool, optional): If true do a left_join so primary rows would be kept even if there are no foreign rows joinable
        Raises:
            Exception: If the primary key is found more than once in the foreign table.
        Returns:
            List of dicts: Each dict is a row of the joined tables (appending the table name to each column name).
        """
        primary_table_list = self.process_table(table_joiner.primary_table_name)
        foreign_table_list = self.process_table(table_joiner.secondary_table_name)
        joined_list = []
        for p_row in primary_table_list:
            # find rows in the foreign table that match with the primary key
            foreign_rows = [f_row for f_row in foreign_table_list if p_row[table_joiner.primary_key] == f_row[table_joiner.foreign_key]]
            if len(foreign_rows) > 1:
                raise Exception("Join of tables returned more than one row")

            salted_p_dict = {table_joiner.primary_table_name+'-'+k: v for k, v in p_row.iteritems()}
            joined_dic = salted_p_dict
            # if there is a row to join, join it, else return the primary row only.
            if len(foreign_rows) == 1:
                salted_f_dict = {table_joiner.secondary_table_name+'-'+k: v for k, v in foreign_rows[0].iteritems()}
                joined_dic.update(salted_f_dict)
            else:
                logger.warn("{} had no row in the foreign table".format(pf(p_row, indent=4)))
                if not left_join:
                    logger.info("Ignored.")
                    continue
            joined_list.append(joined_dic)
        logger.info('{} {} rows found in the database.'.format(len(joined_list), table_joiner.primary_table_name))
        return joined_list


class TableJoiner(object):
    """Information container for joining two tables.
    Attributes:
        foreign_key (str):
        primary_key (str):
        primary_table_name (str):
        secondary_table_name (str):
    """
    primary_table_name = None
    secondary_table_name = None
    primary_key = None
    foreign_key = None

    def __init__(self, primary_table_name, secondary_table_name, primary_key, foreign_key):
        """Set table joiner data."""
        self.primary_table_name = primary_table_name
        self.secondary_table_name = secondary_table_name
        self.primary_key = primary_key
        self.foreign_key = foreign_key
