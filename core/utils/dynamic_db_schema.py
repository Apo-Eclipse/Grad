from django.apps import apps
from django.db import models

def get_dynamic_schema(app_names_list=['core']):
    """
    Generates a rich text schema of Django models for LLM prompts.
    Handles Foreign Keys, OneToOneFields, and Choices automatically.
    """
    schema_text = []

    for app_label in app_names_list:
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            print(f"Warning: App '{app_label}' not found.")
            continue

        for model in app_config.get_models():
            model_name = model.__name__
            # Use the actual DB table name so the LLM writes correct SQL
            table_name = model._meta.db_table 
            
            fields_desc = []

            for field in model._meta.get_fields():
                # Skip reverse relations (like 'budget_set') and non-concrete fields
                if field.auto_created and not field.concrete:
                    continue

                # 1. Basic info: Name and Type
                field_type = field.get_internal_type()
                line = f"- {field.name} ({field_type})"

                # 2. Add Nullability (Important for SQL logic)
                if field.null:
                    line += " [NULLABLE]"

                # 3. Handle Relationships (ForeignKey & OneToOne)
                if field.is_relation and field.related_model:
                    target_model = field.related_model.__name__
                    line += f" -> References Table: {field.related_model._meta.db_table} (Model: {target_model})"

                # 4. Handle Choices (Crucial for your gender/employment fields)
                if field.choices:
                    # field.choices comes as [('1', 'male'), ('2', 'female')]
                    # We convert this to a readable string format: "1": "male", "2": "female"
                    options = [f'"{k}": "{v}"' for k, v in field.choices]
                    line += f" -> Allowed Values: {{{', '.join(options)}}}"

                # 5. Handle Decimal Precision (Good for financial accuracy)
                if isinstance(field, models.DecimalField):
                    line += f" [Precision: {field.max_digits},{field.decimal_places}]"

                fields_desc.append(line)

            # Combine into a clean block
            model_block = (
                f"Table: {table_name} (Model: {model_name})\n"
                f"Columns:\n" + "\n".join(fields_desc)
            )
            schema_text.append(model_block)

    return "\n\n".join(schema_text)