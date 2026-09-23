"""
Tests for normalization module.
"""
import pytest
from app.services.normalization import (
    normalize_reference,
    normalize_description,
    normalize_uom,
    normalize_supplier,
    normalize_whitespace,
    normalize_punctuation,
)


class TestNormalizeReference:
    def test_uppercase(self):
        assert normalize_reference('ctrl-air-01') == 'CTRL-AIR-01'

    def test_whitespace_collapse(self):
        assert normalize_reference('CTRL  -  AIR-01') == 'CTRL-AIR-01'

    def test_punctuation_harmonization_underscore(self):
        assert normalize_reference('CTRL_AIR_01') == 'CTRL-AIR-01'

    def test_punctuation_harmonization_double_dash(self):
        assert normalize_reference('CTRL--AIR-01') == 'CTRL-AIR-01'

    def test_trim(self):
        assert normalize_reference('  CTRL-AIR-01  ') == 'CTRL-AIR-01'

    def test_none_input(self):
        assert normalize_reference(None) is None

    def test_empty_string(self):
        assert normalize_reference('') == ''


class TestNormalizeDescription:
    def test_preserve_case(self):
        assert normalize_description('HVAC Control Unit') == 'HVAC Control Unit'

    def test_whitespace_collapse(self):
        assert normalize_description('HVAC   Control    Unit') == 'HVAC Control Unit'

    def test_trim(self):
        assert normalize_description('  HVAC Control Unit  ') == 'HVAC Control Unit'

    def test_none_input(self):
        assert normalize_description(None) is None

    def test_empty_string(self):
        assert normalize_description('') == ''


class TestNormalizeUOM:
    def test_uppercase(self):
        assert normalize_uom('pcs') == 'PCS'
        assert normalize_uom('ea') == 'EA'

    def test_whitespace_trim(self):
        assert normalize_uom('  pcs  ') == 'PCS'

    def test_none_input(self):
        assert normalize_uom(None) is None


class TestNormalizeSupplier:
    def test_whitespace_collapse(self):
        assert normalize_supplier('Siemens   Mobility') == 'Siemens Mobility'

    def test_trim(self):
        assert normalize_supplier('  Siemens  ') == 'Siemens'

    def test_none_input(self):
        assert normalize_supplier(None) is None


class TestDeterministic:
    def test_same_input_same_output(self):
        test_input = '  Ctrl_AIR-01  '
        result1 = normalize_reference(test_input)
        result2 = normalize_reference(test_input)
        assert result1 == result2


class TestWhitespaceHelper:
    def test_collapse_multiple_spaces(self):
        assert normalize_whitespace('a   b    c') == 'a b c'

    def test_trim(self):
        assert normalize_whitespace('  hello  ') == 'hello'

    def test_none(self):
        assert normalize_whitespace(None) is None


class TestPunctuationHelper:
    def test_underscore_to_dash(self):
        assert normalize_punctuation('CTRL_AIR') == 'CTRL-AIR'

    def test_multiple_dashes(self):
        assert normalize_punctuation('CTRL---AIR') == 'CTRL-AIR'

    def test_leading_trailing_dash(self):
        assert normalize_punctuation('-CTRL-AIR-') == 'CTRL-AIR'

    def test_none(self):
        assert normalize_punctuation(None) is None
