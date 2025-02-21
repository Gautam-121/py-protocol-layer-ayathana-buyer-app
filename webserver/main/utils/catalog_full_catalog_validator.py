import json
from typing import Dict, List, Optional
from datetime import datetime
import re


class CatalogValidator:
    def __init__(self):
        self.errors = []
        
    def validate_catalog(self, catalog_data: Dict) -> List[Dict]:
        """Main validation method that coordinates all checks"""
        self.errors = []  # Reset errors
        
        # Validate context
        self.validate_context(catalog_data.get('context', {}))
        
        # Get provider data
        providers = catalog_data.get('message', {}).get('catalog', {}).get('bpp/providers', [])
        
        # Validate each provider
        for provider in providers:
            self.validate_provider(provider)
            
            # Validate items for each provider
            items = provider.get('items', [])
            for item in items:
                self.validate_item(item, provider['id'],items)
                
        return self.errors
    
    def add_error(self, error_type: str, code: str, path: str, message: str):
        """Helper method to add errors in standard format"""
        self.errors.append({
            "type": error_type,
            "code": code,
            "path": path,
            "message": message
        })

    def validate_context(self, context: Dict):
        """Validate context fields"""
        required_fields = [
            'domain', 'country', 'city', 'action', 'core_version',
            'bap_id', 'bap_uri', 'bpp_id', 'bpp_uri',
            'transaction_id', 'message_id', 'timestamp'
        ]
        
        # Check for missing required fields
        for field in required_fields:
            if field not in context or not context[field]:
                self.add_error("BPP-ERROR", "92003", f"context.{field}", f"Mandatory field {field} missing in context")

        # Validate domain
        valid_domains = ['ONDC:RET10','ONDC:RET11','ONDC:RET12','ONDC:RET13','ONDC:RET14','ONDC:RET15','ONDC:RET16','ONDC:RET17','ONDC:RET18','ONDC:RET19','ONDC:RET20']
        if context.get('domain') not in valid_domains:
            self.add_error("BPP-ERROR", "92004", "context.domain", "Invalid domain sent")

         # Validate country code
        if len(context.get('country', '')) != 3:
            self.add_error("BPP-ERROR", "92004", "context.country", "Country code must be in ISO 3166 Alpha-3 format")

         # Validate city code
        city = context.get('city', '')
        if not (city.startswith("std:") and len(city) > 4):
            self.add_error("BPP-ERROR", "92004", "context.city", "City code must follow the 'std:code' format")

        # Validate action
        if context.get('action') != "on_search":
            self.add_error("BPP-ERROR", "92004", "context.action", "Action must be 'on_search'")

        # Validate core version
        if context.get('core_version') != "1.2.0":
            self.add_error("BPP-ERROR", "92004", "context.core_version", "Core version should be '1.2.0'")

        # Validate data types of specific fields
        string_fields = ['bpp_id', 'bpp_uri', 'transaction_id', 'message_id']
        for field in string_fields:
            if not isinstance(context.get(field), str):
                self.add_error("BPP-ERROR", "92004", f"context.{field}", f"{field} must be a string")

        # Validate timestamp
        try:
            datetime.fromisoformat(context.get('timestamp', '').replace('Z', '+00:00'))
        except (ValueError, TypeError):
            self.add_error("BPP-ERROR", "92004", "context.timestamp", "Timestamp must be a valid ISO 8601 datetime string")

        # Validate TTL (Time To Live)
        ttl = context.get('ttl')
        if ttl:
            if not isinstance(ttl, str) or not ttl.startswith('PT') or not ttl.endswith('S'):
                self.add_error("BPP-ERROR", "92004", "context.ttl", "TTL must be in the format 'PT30S'")


    def validate_provider(self, provider: Dict):
        """Validate provider level information"""
        provider_id = provider.get('id')
        base_path = f"message.catalog.bpp/providers[?(@.id=='{provider_id}')]"
        
        # Check for provider ID
        if not provider_id:
            self.add_error(
                "PROVIDER-ERROR",
                "90019",
                base_path,
                "Provider ID missing"
            )
            
        # Validate location
        locations = provider.get('locations', [])
        for location in locations:
            self.validate_location(location, provider_id)
            
        # Validate fulfillments
        fulfillments = provider.get('fulfillments', [])
        if not fulfillments:
            self.add_error(
                "PROVIDER-ERROR",
                "90019",
                f"{base_path}.fulfillments",
                "Fulfillment details missing"
        )
        else:
            for idx, fulfillment in enumerate(fulfillments):
                fulfillment_path = f"{base_path}.fulfillments[{idx}]"
                if not fulfillment.get('id'):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{fulfillment_path}.id",
                        "Fulfillment ID missing"
                    )
                if not fulfillment.get('type'):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{fulfillment_path}.type",
                        "Fulfillment type missing"
                    )
                contact = fulfillment.get('contact')
                if not contact:
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{fulfillment_path}.contact",
                        "Fulfillment contact details missing"
                    )
                else:
                    phone = contact.get('phone')
                    email = contact.get('email')
                
                    # Validate phone number (Indian phone number)
                    if not phone or not re.fullmatch(r'^[789]\d{9}$', phone):
                        self.add_error(
                            "PROVIDER-ERROR",
                            "90019",
                            f"{fulfillment_path}.contact.phone",
                            "Invalid Indian phone number"
                        )
                
                    # Validate email address (general email validation)
                    if not email or not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        self.add_error(
                            "PROVIDER-ERROR",
                            "90019",
                            f"{fulfillment_path}.contact.email",
                            "Invalid email address"
                        )
            
        # Validate store timing
        self.validate_store_timing(provider, base_path)

    def validate_location(self, location: Dict, provider_id: str):
        """Validate location information"""
        base_path = f"message.catalog.bpp/providers[?(@.id=='{provider_id}')].locations"
    
        # Validate GPS coordinates
        gps = location.get('gps', '').split(',')
        if len(gps) != 2:
            self.add_error(
                "PROVIDER-ERROR",
                "90019",
                f"{base_path}.gps",
                 "Invalid GPS coordinates format"
            )
        else:
            try:
                lat, lon = float(gps[0]), float(gps[1])
                if not (-90 <= lat <= 90):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.gps",
                        "Invalid Latitude"
                    )
                if not (-180 <= lon <= 180):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.gps",
                        "Invalid Longitude"
                    )
            except ValueError:
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.gps",
                        "Invalid GPS coordinates values"
                    )
    
            # Validate address
            address = location.get('address', {})
            required_address_fields = ['locality', 'street', 'city', 'area_code', 'state']
            for field in required_address_fields:
                if not address.get(field):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.address.{field}",
                        f"Empty Address field: {field}"
                    )
    
            # Validate time
            time = location.get('time', {})
            if time:
                # Validate label
                label = time.get('label')
                if label not in ['enable', 'disable']:
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.time.label",
                        "Invalid time label"
                    )

            # Validate timestamp
            timestamp = time.get('timestamp')
            if not timestamp or not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', timestamp):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.time.timestamp",
                        "Invalid timestamp format"
                    )
        
    

            # Validate circle (if exists)
            circle = location.get('circle', {})
            if circle:
                # Validate circle gps
                circle_gps = circle.get('gps', '').split(',')
                if len(circle_gps) != 2:
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.circle.gps",
                        "Invalid Circle GPS coordinates format"
                    )
            else:
                try:
                    lat, lon = float(circle_gps[0]), float(circle_gps[1])
                    if not (-90 <= lat <= 90):
                        self.add_error(
                            "PROVIDER-ERROR",
                            "90019",
                            f"{base_path}.circle.gps",
                            "Invalid Latitude in circle"
                        )
                    if not (-180 <= lon <= 180):
                        self.add_error(
                            "PROVIDER-ERROR",
                            "90019",
                            f"{base_path}.circle.gps",
                            "Invalid Longitude in circle"
                        )
                except ValueError:
                        self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.circle.gps",
                        "Invalid Circle GPS coordinates values"
                    )
        
            # Validate radius
            radius = circle.get('radius', {})
            if radius:
                value = radius.get('value')
                unit = radius.get('unit')

                # Convert value to a number if it's a string and valid numeric
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                         value = None

                if not value or not isinstance(value, (int, float)):
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.circle.radius.value",
                        "Invalid radius value"
                    )
            if unit not in ['km', 'miles']:
                    self.add_error(
                        "PROVIDER-ERROR",
                        "90019",
                        f"{base_path}.circle.radius.unit",
                        "Invalid radius unit"
                    )

    def validate_store_timing(self, provider: Dict, base_path: str):
        """Validate store timing information"""
        locations = provider.get('locations', [])
        for location in locations:
            time_info = location.get('time', {})
            
            if not time_info:
                self.add_error(
                    "PROVIDER-ERROR",
                    "90019",
                    f"{base_path}.time",
                    "Store timing not provided"
                )
                continue

    def validate_item(self, item: Dict, provider_id: str, all_items: List[Dict]):
        """Validate item level information"""
        item_id = item.get('id')
        category_id = item.get("category_id")
        base_path = f"message.catalog.bpp/providers[?(@.id=='{provider_id}')].items[?(@.id=='{item_id}')]"

         # Check for provider ID
        if not item_id:
            self.add_error(
                "PROVIDER-ERROR",
                "91026",
                base_path,
                "Invalid Item ID"
            )

         # Check for provider ID
        if not category_id:
            self.add_error(
                "PROVIDER-ERROR",
                "91021",
                base_path,
                "Category field is missing"
            )

        # Check for duplicate product
        duplicate_items = [i for i in all_items if i.get('id') == item_id and i != item]
        if duplicate_items:
            self.add_error(
                "ITEM-ERROR",
                "91008",
                base_path,
                "Duplicate Product"
            )

        # Check for net quantity
        if not item.get("quantity"):
            self.add_error(
                "ITEM-ERROR",
                "91013",
                base_path,
                "Net Quantity not present"
            )

        # Check for FSSAI/Statutory requirement
        if not item.get('@ondc/org/statutory_reqs_packaged_commodities'):
            self.add_error(
                "ITEM-ERROR",
                "91014",
                base_path,
                "FSSAI/Statutory requirement not present"
        )
            
        
        # Validate price
        self.validate_price(item, base_path)
        
        # Validate images
        self.validate_images(item, base_path)
        
        # # Validate statutory requirements
        self.validate_statutory_requirements(item, base_path)
        
        # Validate quantity
        self.validate_quantity(item, base_path)
        
        # # Validate customer care details
        self.validate_customer_care(item, base_path)

        # Check for country of origin
        country_of_origin = self.get_tag_value(item, "origin", "country")
        if not country_of_origin:
            self.add_error(
                "ITEM-ERROR",
                "91012",
                base_path,
                "Country of Origin not present"
            )

    def validate_price(self, item: Dict, base_path: str):
        """Validate item price information"""
        price = item.get('price', {})
        maximum_value = float(price.get('maximum_value', 0))
        value = float(price.get('value', 0))
        
        if value <= 0:
            self.add_error(
                "ITEM-ERROR",
                "91010",
                f"{base_path}.price",
                "Price less than zero"
            )
            
        if value > maximum_value:
            self.add_error(
                "ITEM-ERROR",
                "91001",
                f"{base_path}.price",
                "Item price > MRP"
            )

    def validate_images(self, item: Dict, base_path: str):
        """Validate item images"""
        images = item.get('descriptor', {}).get('images', [])
        
        if not images:
            self.add_error(
                "ITEM-ERROR",
                "91003",
                f"{base_path}.descriptor.images",
                "No Images found"
            )
            
        # Check for duplicate images
        if len(images) != len(set(images)):
            self.add_error(
                "ITEM-ERROR",
                "91004",
                f"{base_path}.descriptor.images",
                "Duplicate Images Found"
            )

    def validate_statutory_requirements(self, item: Dict, base_path: str):
        """Validate statutory requirements"""
        statutory = item.get('@ondc/org/statutory_reqs_packaged_commodities', {})
        
        required_fields = [
            'manufacturer_or_packer_name',
            'manufacturer_or_packer_address',
            'common_or_generic_name_of_commodity',
            'month_year_of_manufacture_packing_import'
        ]
        
        for field in required_fields:
            if not statutory.get(field):
                self.add_error(
                    "ITEM-ERROR",
                    "91007",
                    f"{base_path}.@ondc/org/statutory_reqs_packaged_commodities.{field}",
                    f"Mandatory statutory field missing: {field}"
                )

    def validate_quantity(self, item: Dict, base_path: str):
        """Validate item quantity information"""
        quantity = item.get('quantity', {})
        available = quantity.get('available', {}).get('count')
        
        if not available or not str(available).isdigit():
            self.add_error(
                "ITEM-ERROR",
                "91018",
                f"{base_path}.quantity",
                "Available quantity for the SKU is either absent or invalid"
            )

    def validate_customer_care(self, item: Dict, base_path: str):
        """Validate customer care details"""
        customer_care = item.get('@ondc/org/contact_details_consumer_care')
        
        if not customer_care:
            self.add_error(
                "ITEM-ERROR",
                "91022",
                f"{base_path}.@ondc/org/contact_details_consumer_care",
                "Customer care contact details missing"
            )
        else:
            # Check format (name,email,phone)
            parts = customer_care.split(',')
            if len(parts) != 3:
                self.add_error(
                    "ITEM-ERROR",
                    "91022",
                    f"{base_path}.@ondc/org/contact_details_consumer_care",
                    "Customer care contact details format incorrect"
                )

    def get_tag_value(self, item: Dict, code: str, value: str) -> str:
        """Get value for a specific tag"""
        for tag in item.get('tags', []):
            if tag.get('code') == code:
                for v in tag.get('list', []):
                    if v.get('code') == value:
                        return v.get('value')
            return ""


 