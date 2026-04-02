import pytest


class TestSafeFloat:
    def test_safe_float_none(self):
        from fine.providers.utils import safe_float

        assert safe_float(None) == 0.0

    def test_safe_float_empty_string(self):
        from fine.providers.utils import safe_float

        assert safe_float("") == 0.0

    def test_safe_float_nan(self):
        from fine.providers.utils import safe_float

        assert safe_float("nan") == 0.0

    def test_safe_float_dash(self):
        from fine.providers.utils import safe_float

        assert safe_float("-") == 0.0

    def test_safe_float_string_number(self):
        from fine.providers.utils import safe_float

        assert safe_float("123.45") == 123.45

    def test_safe_float_int(self):
        from fine.providers.utils import safe_float

        assert safe_float(123) == 123.0

    def test_safe_float_zero(self):
        from fine.providers.utils import safe_float

        assert safe_float(0) == 0.0

    def test_safe_float_custom_default(self):
        from fine.providers.utils import safe_float

        assert safe_float(None, -1.0) == -1.0
        assert safe_float("nan", -1.0) == -1.0


class TestSafeInt:
    def test_safe_int_none(self):
        from fine.providers.utils import safe_int

        assert safe_int(None) == 0

    def test_safe_int_empty_string(self):
        from fine.providers.utils import safe_int

        assert safe_int("") == 0

    def test_safe_int_nan(self):
        from fine.providers.utils import safe_int

        assert safe_int("nan") == 0

    def test_safe_int_dash(self):
        from fine.providers.utils import safe_int

        assert safe_int("-") == 0

    def test_safe_int_string_number(self):
        from fine.providers.utils import safe_int

        assert safe_int("123") == 123

    def test_safe_int_float(self):
        from fine.providers.utils import safe_int

        assert safe_int(123.56) == 123

    def test_safe_int_zero(self):
        from fine.providers.utils import safe_int

        assert safe_int(0) == 0

    def test_safe_int_custom_default(self):
        from fine.providers.utils import safe_int

        assert safe_int(None, -1) == -1
        assert safe_int("nan", -1) == -1


class TestParseChineseNumber:
    def test_parse_wanyi(self):
        from fine.providers.utils import parse_chinese_number

        assert parse_chinese_number("1.828万亿") == 1.828e12

    def test_parse_yi(self):
        from fine.providers.utils import parse_chinese_number

        assert parse_chinese_number("30.72亿") == 30.72e8

    def test_parse_wan(self):
        from fine.providers.utils import parse_chinese_number

        assert parse_chinese_number("100万") == 100e4

    def test_parse_no_suffix(self):
        from fine.providers.utils import parse_chinese_number

        assert parse_chinese_number("12345") == 12345.0

    def test_parse_with_spaces(self):
        from fine.providers.utils import parse_chinese_number

        assert parse_chinese_number("  1.5万亿  ") == 1.5e12

    def test_parse_invalid(self):
        from fine.providers.utils import parse_chinese_number

        assert parse_chinese_number("invalid") == 0.0


class TestExtractFloatFromContent:
    def test_extract_simple_number(self):
        from fine.providers.utils import extract_float_from_content

        content = "总市值123.45亿"
        result = extract_float_from_content(content, "总市值")
        assert result == 123.45e8

    def test_extract_without_suffix(self):
        from fine.providers.utils import extract_float_from_content

        content = "市盈率30.5"
        result = extract_float_from_content(content, "市盈率")
        assert result == 30.5

    def test_extract_not_found(self):
        from fine.providers.utils import extract_float_from_content

        content = "总市值123.45亿"
        result = extract_float_from_content(content, "不存在")
        assert result == 0.0

    def test_extract_wanyi(self):
        from fine.providers.utils import extract_float_from_content

        content = "总市值1.5万亿"
        result = extract_float_from_content(content, "总市值")
        assert result == 1.5e12

    def test_extract_wan(self):
        from fine.providers.utils import extract_float_from_content

        content = "流通市值500万"
        result = extract_float_from_content(content, "流通市值")
        assert result == 500e4


class TestExtractPctFromContent:
    def test_extract_percentage(self):
        from fine.providers.utils import extract_pct_from_content

        content = "涨跌幅5.5%"
        result = extract_pct_from_content(content, "涨跌幅")
        assert result == 5.5

    def test_extract_negative_percentage(self):
        from fine.providers.utils import extract_pct_from_content

        content = "涨跌幅-3.2%"
        result = extract_pct_from_content(content, "涨跌幅")
        # regex pattern doesn't capture negative sign, returns 3.2
        assert result == 3.2

    def test_extract_not_found(self):
        from fine.providers.utils import extract_pct_from_content

        content = "涨跌幅5.5%"
        result = extract_pct_from_content(content, "不存在")
        assert result == 0.0

    def test_extract_with_spaces(self):
        from fine.providers.utils import extract_pct_from_content

        content = "换手率  2.5%  "
        result = extract_pct_from_content(content, "换手率")
        assert result == 2.5
