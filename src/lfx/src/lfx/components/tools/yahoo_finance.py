import ast
import pprint
from enum import Enum
import i18n

from langchain.tools import StructuredTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import DropdownInput, IntInput, MessageTextInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class YahooFinanceMethod(Enum):
    GET_INFO = "get_info"
    GET_NEWS = "get_news"
    GET_ACTIONS = "get_actions"
    GET_ANALYSIS = "get_analysis"
    GET_BALANCE_SHEET = "get_balance_sheet"
    GET_CALENDAR = "get_calendar"
    GET_CASHFLOW = "get_cashflow"
    GET_INSTITUTIONAL_HOLDERS = "get_institutional_holders"
    GET_RECOMMENDATIONS = "get_recommendations"
    GET_SUSTAINABILITY = "get_sustainability"
    GET_MAJOR_HOLDERS = "get_major_holders"
    GET_MUTUALFUND_HOLDERS = "get_mutualfund_holders"
    GET_INSIDER_PURCHASES = "get_insider_purchases"
    GET_INSIDER_TRANSACTIONS = "get_insider_transactions"
    GET_INSIDER_ROSTER_HOLDERS = "get_insider_roster_holders"
    GET_DIVIDENDS = "get_dividends"
    GET_CAPITAL_GAINS = "get_capital_gains"
    GET_SPLITS = "get_splits"
    GET_SHARES = "get_shares"
    GET_FAST_INFO = "get_fast_info"
    GET_SEC_FILINGS = "get_sec_filings"
    GET_RECOMMENDATIONS_SUMMARY = "get_recommendations_summary"
    GET_UPGRADES_DOWNGRADES = "get_upgrades_downgrades"
    GET_EARNINGS = "get_earnings"
    GET_INCOME_STMT = "get_income_stmt"


class YahooFinanceSchema(BaseModel):
    symbol: str = Field(...,
                        description="The stock symbol to retrieve data for.")
    method: YahooFinanceMethod = Field(
        YahooFinanceMethod.GET_INFO, description="The type of data to retrieve.")
    num_news: int | None = Field(
        5, description="The number of news articles to retrieve.")


class YfinanceToolComponent(LCToolComponent):
    display_name = i18n.t('components.tools.yahoo_finance.display_name')
    description = i18n.t('components.tools.yahoo_finance.description')
    icon = "trending-up"
    name = "YahooFinanceTool"
    legacy = True
    replacement = ["yahoosearch.YfinanceComponent"]

    inputs = [
        MessageTextInput(
            name="symbol",
            display_name=i18n.t(
                'components.tools.yahoo_finance.symbol.display_name'),
            info=i18n.t('components.tools.yahoo_finance.symbol.info'),
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t(
                'components.tools.yahoo_finance.method.display_name'),
            info=i18n.t('components.tools.yahoo_finance.method.info'),
            options=list(YahooFinanceMethod),
            value="get_news",
        ),
        IntInput(
            name="num_news",
            display_name=i18n.t(
                'components.tools.yahoo_finance.num_news.display_name'),
            info=i18n.t('components.tools.yahoo_finance.num_news.info'),
            value=5,
        ),
    ]

    def run_model(self) -> list[Data]:
        try:
            if not self.symbol or not self.symbol.strip():
                warning_message = i18n.t(
                    'components.tools.yahoo_finance.warnings.empty_symbol')
                self.status = warning_message
                return [Data(data={"error": warning_message})]

            executing_message = i18n.t('components.tools.yahoo_finance.info.retrieving_data',
                                       symbol=self.symbol, method=self.method.value)
            self.status = executing_message

            return self._yahoo_finance_tool(
                self.symbol,
                self.method,
                self.num_news,
            )
        except Exception as e:
            error_message = i18n.t(
                'components.tools.yahoo_finance.errors.execution_failed', error=str(e))
            self.status = error_message
            logger.debug("Error in run_model", exc_info=True)
            return [Data(data={"error": error_message, "symbol": self.symbol})]

    def build_tool(self) -> Tool:
        try:
            tool = StructuredTool.from_function(
                name="yahoo_finance",
                description=i18n.t(
                    'components.tools.yahoo_finance.tool_description'),
                func=self._yahoo_finance_tool,
                args_schema=YahooFinanceSchema,
            )

            success_message = i18n.t(
                'components.tools.yahoo_finance.success.tool_created')
            self.status = success_message
            return tool

        except Exception as e:
            error_message = i18n.t(
                'components.tools.yahoo_finance.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _yahoo_finance_tool(
        self,
        symbol: str,
        method: YahooFinanceMethod,
        num_news: int | None = 5,
    ) -> list[Data]:
        try:
            import yfinance as yf
        except ImportError as e:
            error_message = i18n.t(
                'components.tools.yahoo_finance.errors.import_error')
            raise ImportError(error_message) from e

        if not symbol or not symbol.strip():
            error_message = i18n.t(
                'components.tools.yahoo_finance.errors.empty_symbol')
            raise ToolException(error_message)

        try:
            ticker = yf.Ticker(symbol.upper())

            # Convert string method to enum if needed
            if isinstance(method, str):
                try:
                    method = YahooFinanceMethod(method.lower())
                except ValueError:
                    error_message = i18n.t(
                        'components.tools.yahoo_finance.errors.invalid_method', method=method)
                    raise ToolException(error_message)

            if method == YahooFinanceMethod.GET_INFO:
                result = ticker.info
                if not result:
                    error_message = i18n.t(
                        'components.tools.yahoo_finance.errors.no_info_data', symbol=symbol)
                    raise ToolException(error_message)
            elif method == YahooFinanceMethod.GET_NEWS:
                result = ticker.news
                if not result:
                    error_message = i18n.t(
                        'components.tools.yahoo_finance.errors.no_news_data', symbol=symbol)
                    raise ToolException(error_message)
                # Limit news articles if num_news is specified
                if num_news and num_news > 0:
                    result = result[:num_news]
            else:
                # For all other methods, call the method on the ticker
                try:
                    result = getattr(ticker, method.value)()
                    if result is None or (hasattr(result, 'empty') and result.empty):
                        error_message = i18n.t('components.tools.yahoo_finance.errors.no_data_available',
                                               method=method.value, symbol=symbol)
                        raise ToolException(error_message)
                except AttributeError:
                    error_message = i18n.t(
                        'components.tools.yahoo_finance.errors.method_not_found', method=method.value)
                    raise ToolException(error_message)

            # Format result for display
            formatted_result = pprint.pformat(result)

            # Create Data objects based on method type
            if method == YahooFinanceMethod.GET_NEWS:
                if isinstance(result, str):
                    try:
                        # If result is string, try to parse it
                        parsed_result = ast.literal_eval(result)
                        data_list = [Data(data=article)
                                     for article in parsed_result]
                    except (ValueError, SyntaxError):
                        # If parsing fails, return as single data item
                        data_list = [
                            Data(data={"news": result, "symbol": symbol})]
                else:
                    # If result is already a list/dict
                    data_list = [Data(data=article) for article in result]
            else:
                data_list = [Data(
                    data={"result": formatted_result, "symbol": symbol, "method": method.value})]

            success_message = i18n.t('components.tools.yahoo_finance.success.data_retrieved',
                                     method=method.value, symbol=symbol, count=len(data_list))
            logger.debug(success_message)

            return data_list

        except ToolException:
            # Re-raise ToolException as is (already has i18n message)
            raise
        except Exception as e:
            error_message = i18n.t('components.tools.yahoo_finance.errors.data_retrieval_failed',
                                   method=method.value, symbol=symbol, error=str(e))
            logger.debug("Error retrieving Yahoo Finance data", exc_info=True)
            raise ToolException(error_message) from e
