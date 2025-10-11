import random
from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import IntInput, MessageTextInput, DropdownInput, Output
from lfx.schema.data import Data


class MockDataGeneratorComponent(Component):
    """Mock Data Generator Component.

    Generates sample data for testing and development purposes. Supports three main
    Langflow output types: Message (text), Data (JSON), and DataFrame (tabular data).

    This component is useful for:
    - Testing workflows without real data sources
    - Prototyping data processing pipelines
    - Creating sample data for demonstrations
    - Development and debugging of Langflow components
    """

    display_name = "Mock Data"
    description = "Generate mock data for testing and development."
    icon = "database"
    name = "MockData"

    inputs = [
        IntInput(
            name="number_of_rows",
            display_name=i18n.t(
                'components.data.mock_data.number_of_rows.display_name'),
            info=i18n.t('components.data.mock_data.number_of_rows.info'),
            value=10,
            range_spec=RangeSpec(min=1, max=1000, step=1),
        ),
        DropdownInput(
            name="data_type",
            display_name=i18n.t(
                'components.data.mock_data.data_type.display_name'),
            info=i18n.t('components.data.mock_data.data_type.info'),
            options=["user_profiles", "products",
                     "transactions", "articles", "custom"],
            value="user_profiles",
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="custom_schema",
            display_name=i18n.t(
                'components.data.mock_data.custom_schema.display_name'),
            info=i18n.t('components.data.mock_data.custom_schema.info'),
            placeholder='{"name": "string", "age": "integer", "email": "email"}',
            show=False,
        ),
        IntInput(
            name="seed",
            display_name=i18n.t('components.data.mock_data.seed.display_name'),
            info=i18n.t('components.data.mock_data.seed.info'),
            value=42,
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.mock_data.text_key.display_name'),
            info=i18n.t('components.data.mock_data.text_key.info'),
            value="text",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Result", name="dataframe_output",
               method="generate_dataframe_output"),
        Output(display_name="Result", name="message_output",
               method="generate_message_output"),
        Output(display_name="Result", name="data_output",
               method="generate_data_output"),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide custom schema field based on data type selection."""
        if field_name == "data_type":
            if field_value == "custom":
                build_config["custom_schema"]["show"] = True
            else:
                build_config["custom_schema"]["show"] = False
        return build_config

    def generate_mock_data(self) -> list[Data]:
        try:
            if self.seed:
                random.seed(self.seed)

            if self.number_of_rows <= 0:
                error_message = i18n.t(
                    'components.data.mock_data.errors.invalid_row_count')
                self.status = error_message
                raise ValueError(error_message)

            if self.data_type == "user_profiles":
                data_list = self._generate_user_profiles()
            elif self.data_type == "products":
                data_list = self._generate_products()
            elif self.data_type == "transactions":
                data_list = self._generate_transactions()
            elif self.data_type == "articles":
                data_list = self._generate_articles()
            elif self.data_type == "custom":
                if not self.custom_schema:
                    error_message = i18n.t(
                        'components.data.mock_data.errors.missing_custom_schema')
                    self.status = error_message
                    raise ValueError(error_message)
                data_list = self._generate_custom_data()
            else:
                error_message = i18n.t(
                    'components.data.mock_data.errors.invalid_data_type', data_type=self.data_type)
                self.status = error_message
                raise ValueError(error_message)

            result = [Data(data=item, text_key=self.text_key)
                      for item in data_list]

            self.status = f"Generated {len(result)} mock data records"
            return result

        except Exception as e:
            error_message = i18n.t(
                'components.data.mock_data.errors.generation_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _generate_user_profiles(self) -> list[dict]:
        """Generate mock user profile data."""
        first_names = ["John", "Jane", "Bob", "Alice",
                       "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones",
                      "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        domains = ["gmail.com", "yahoo.com",
                   "outlook.com", "company.com", "university.edu"]

        profiles = []
        for i in range(self.number_of_rows):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            profiles.append({
                "id": i + 1,
                "first_name": first_name,
                "last_name": last_name,
                "email": f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}",
                "age": random.randint(18, 80),
                "city": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
                "text": f"{first_name} {last_name} is {random.randint(18, 80)} years old"
            })
        return profiles

    def _generate_products(self) -> list[dict]:
        """Generate mock product data."""
        categories = ["Electronics", "Clothing",
                      "Books", "Home & Garden", "Sports"]
        products = []
        for i in range(self.number_of_rows):
            category = random.choice(categories)
            products.append({
                "id": i + 1,
                "name": f"Product {i + 1}",
                "category": category,
                "price": round(random.uniform(10.0, 500.0), 2),
                "stock": random.randint(0, 100),
                "rating": round(random.uniform(1.0, 5.0), 1),
                "text": f"Product {i + 1} in {category} category"
            })
        return products

    def _generate_transactions(self) -> list[dict]:
        """Generate mock transaction data."""
        transactions = []
        for i in range(self.number_of_rows):
            amount = round(random.uniform(10.0, 1000.0), 2)
            transactions.append({
                "id": i + 1,
                "user_id": random.randint(1, 100),
                "amount": amount,
                "currency": random.choice(["USD", "EUR", "GBP", "JPY"]),
                "status": random.choice(["completed", "pending", "failed"]),
                "timestamp": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                "text": f"Transaction {i + 1} for ${amount}"
            })
        return transactions

    def _generate_articles(self) -> list[dict]:
        """Generate mock article data."""
        topics = ["Technology", "Science",
                  "Politics", "Sports", "Entertainment"]
        articles = []
        for i in range(self.number_of_rows):
            topic = random.choice(topics)
            articles.append({
                "id": i + 1,
                "title": f"{topic} Article {i + 1}",
                "author": f"Author {random.randint(1, 20)}",
                "topic": topic,
                "word_count": random.randint(500, 2000),
                "views": random.randint(100, 10000),
                "likes": random.randint(10, 500),
                "text": f"This is {topic} article {i + 1} with {random.randint(500, 2000)} words"
            })
        return articles

    def _generate_custom_data(self) -> list[dict]:
        """Generate mock data based on custom schema."""
        import json
        try:
            schema = json.loads(self.custom_schema)
            data_list = []

            for i in range(self.number_of_rows):
                item = {"id": i + 1}
                for field, field_type in schema.items():
                    if field_type == "string":
                        item[field] = f"Sample {field} {i + 1}"
                    elif field_type == "integer":
                        item[field] = random.randint(1, 100)
                    elif field_type == "float":
                        item[field] = round(random.uniform(1.0, 100.0), 2)
                    elif field_type == "email":
                        item[field] = f"user{i + 1}@example.com"
                    elif field_type == "boolean":
                        item[field] = random.choice([True, False])
                    else:
                        item[field] = f"Unknown type: {field_type}"

                # Add text field if not already present
                if "text" not in item:
                    item["text"] = f"Custom data record {i + 1}"

                data_list.append(item)

            return data_list

        except json.JSONDecodeError as e:
            error_message = i18n.t(
                'components.data.mock_data.errors.invalid_schema', error=str(e))
            raise ValueError(error_message) from e
