export interface paths {
    "/{rest_of_path}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        /** Preflight Handler */
        options: operations["preflight_handler__rest_of_path__options"];
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register User */
        post: operations["register_user_api_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login For Access Token */
        post: operations["login_for_access_token_api_token_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/users/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Users Me */
        get: operations["read_users_me_api_users_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Item */
        post: operations["create_item_api_items__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items_api_items_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/export/data": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Items */
        get: operations["export_items_api_items_export_data_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/barcode/{barcode}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Lookup By Barcode */
        get: operations["lookup_by_barcode_api_items_barcode__barcode__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Item */
        get: operations["get_item_api_items__item_id__get"];
        /** Update Item */
        put: operations["update_item_api_items__item_id__put"];
        post?: never;
        /** Delete Item */
        delete: operations["delete_item_api_items__item_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/bulk-delete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bulk Delete Items */
        post: operations["bulk_delete_items_api_items_bulk_delete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Categories */
        get: operations["get_categories_api_categories_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/locations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Locations */
        get: operations["get_locations_api_locations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Items */
        post: operations["import_items_api_items_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/items/{item_id}/images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Item Images */
        get: operations["list_item_images_api_items__item_id__images_get"];
        put?: never;
        /** Upload Item Image */
        post: operations["upload_item_image_api_items__item_id__images_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/images/{image_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Image */
        delete: operations["delete_image_api_images__image_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/analytics/value-by-category": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Value By Category */
        get: operations["get_value_by_category_api_analytics_value_by_category_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/analytics/value-by-location": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Value By Location */
        get: operations["get_value_by_location_api_analytics_value_by_location_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/analytics/value-trends": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Value Trends */
        get: operations["get_value_trends_api_analytics_value_trends_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/analytics/warranty-status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Warranty Status */
        get: operations["get_warranty_status_api_analytics_warranty_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/analytics/age-analysis": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Age Analysis */
        get: operations["get_age_analysis_api_analytics_age_analysis_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backups": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Backups */
        get: operations["list_backups_api_backups_get"];
        put?: never;
        /**
         * Create Backup
         * @description Enqueue a backup when the ARQ worker is active, otherwise run inline.
         *
         *     The response shape is discriminated:
         *     * ``{ kind: "job", job_id }`` → caller should poll
         *       ``GET /api/jobs/{job_id}`` until the status is ``complete``.
         *     * ``Backup`` (the full resource) → sync path; the backup row is
         *       already persisted and listed.
         */
        post: operations["create_backup_api_backups_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backups/{backup_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore Backup */
        post: operations["restore_backup_api_backups__backup_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backups/upload": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload Backup */
        post: operations["upload_backup_api_backups_upload_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backups/{backup_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Backup */
        delete: operations["delete_backup_api_backups__backup_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backups/{backup_id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download Backup */
        get: operations["download_backup_api_backups__backup_id__download_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ebay/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Categories
         * @description Get available eBay categories and optionally get a suggested category for an item.
         */
        get: operations["list_categories_api_ebay_categories_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ebay/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Export To Ebay
         * @description Export selected items as an eBay-compatible CSV, streamed directly.
         *
         *     v2.3: replaced the prior EbayExportResponse shape (which returned
         *     ``file_url=None`` with a TODO to wire up file storage) with a
         *     streaming CSV response, matching the pattern the new Facebook
         *     Marketplace exporter uses. Callers download the bytes instead of
         *     following a download URL.
         */
        post: operations["export_to_ebay_api_ebay_export_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ebay/items/{item_id}/ebay-fields": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Update Ebay Fields
         * @description Update eBay-specific fields for an item.
         */
        post: operations["update_ebay_fields_api_ebay_items__item_id__ebay_fields_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/facebook/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Categories
         * @description Return the curated list of Facebook Marketplace categories.
         */
        get: operations["list_categories_api_facebook_categories_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/facebook/items/{item_id}/fb-fields": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Update Fb Fields
         * @description Persist FbFields into ``item.custom_fields.facebook``.
         */
        post: operations["update_fb_fields_api_facebook_items__item_id__fb_fields_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/facebook/items/{item_id}/copy-paste": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Generate Copy Paste Block
         * @description Render the item as an FbCopyPasteBlock for the web-form workflow.
         */
        post: operations["generate_copy_paste_block_api_facebook_items__item_id__copy_paste_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/facebook/items/{item_id}/images.zip": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download Images Zip
         * @description Stream a zip of the item's images for FB's bulk upload form.
         */
        get: operations["download_images_zip_api_facebook_items__item_id__images_zip_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/facebook/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Export Catalog Csv
         * @description Stream a CSV matching Meta's Commerce Manager catalog feed spec.
         */
        post: operations["export_catalog_csv_api_facebook_export_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Job */
        get: operations["get_job_api_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/vision/identify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Identify Item */
        post: operations["identify_item_api_vision_identify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Check */
        get: operations["health_check_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Backup */
        Backup: {
            /**
             * Id
             * Format: uuid4
             */
            id: string;
            /**
             * Owner Id
             * Format: uuid4
             */
            owner_id: string;
            /** Filename */
            filename: string;
            /** File Path */
            file_path: string;
            /** Size Bytes */
            size_bytes: number;
            /** Item Count */
            item_count: number;
            /** Image Count */
            image_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Status */
            status: string;
            /** Error Message */
            error_message?: string | null;
        };
        /** BackupList */
        BackupList: {
            /** Backups */
            backups: components["schemas"]["Backup"][];
        };
        /** Body_identify_item_api_vision_identify_post */
        Body_identify_item_api_vision_identify_post: {
            /**
             * Files
             * @description 1..VISION_MAX_IMAGES_PER_REQUEST photos
             */
            files: string[];
            /**
             * Hints
             * @description Optional JSON blob with user-supplied hints (brand, model, etc.).
             */
            hints?: string | null;
        };
        /** Body_import_items_api_items_import_post */
        Body_import_items_api_items_import_post: {
            /** File */
            file: string;
        };
        /** Body_login_for_access_token_api_token_post */
        Body_login_for_access_token_api_token_post: {
            /** Grant Type */
            grant_type?: string | null;
            /** Username */
            username: string;
            /**
             * Password
             * Format: password
             */
            password: string;
            /**
             * Scope
             * @default
             */
            scope?: string;
            /** Client Id */
            client_id?: string | null;
            /**
             * Client Secret
             * Format: password
             */
            client_secret?: string | null;
        };
        /** Body_upload_backup_api_backups_upload_post */
        Body_upload_backup_api_backups_upload_post: {
            /** File */
            file: string;
        };
        /** Body_upload_item_image_api_items__item_id__images_post */
        Body_upload_item_image_api_items__item_id__images_post: {
            /** File */
            file: string;
        };
        /** BulkDeleteRequest */
        BulkDeleteRequest: {
            /** Item Ids */
            item_ids: string[];
        };
        /**
         * CustomFieldsSchema
         * @description Structured shape of ``Item.custom_fields``.
         *
         *     Top-level is strict: only ``ebay``, ``facebook``, and ``user_defined``
         *     are accepted. Unknown keys at this level produce a 422 at request
         *     time — this is the v2.3 plug for the "JSON column accepts anything"
         *     gap flagged in the post-2.0 audit. The ``user_defined`` catchall
         *     preserves the operator-level flexibility that people actually use
         *     (hand-added tags, photography rating, loaner tracking, etc.) without
         *     giving up the schema discipline around the integrations.
         */
        CustomFieldsSchema: {
            ebay?: components["schemas"]["EbayFields"] | null;
            facebook?: components["schemas"]["FbFields"] | null;
            /** User Defined */
            user_defined?: {
                [key: string]: unknown;
            };
        };
        /**
         * EbayCategory
         * @description Schema for eBay category information
         */
        EbayCategory: {
            /**
             * Id
             * @description eBay category ID
             */
            id: string;
            /**
             * Name
             * @description Category name
             */
            name: string;
            /**
             * Subcategories
             * @description Subcategories
             */
            subcategories?: components["schemas"]["EbayCategory"][] | null;
        };
        /**
         * EbayCategoryResponse
         * @description Schema for eBay category lookup response
         */
        EbayCategoryResponse: {
            /**
             * Categories
             * @description List of available categories
             */
            categories: components["schemas"]["EbayCategory"][];
            /** @description Suggested category based on item */
            suggested_category?: components["schemas"]["EbayCategory"] | null;
        };
        /**
         * EbayCondition
         * @enum {string}
         */
        EbayCondition: "NEW" | "LIKE_NEW" | "VERY_GOOD" | "GOOD" | "ACCEPTABLE" | "FOR_PARTS";
        /**
         * EbayDuration
         * @enum {string}
         */
        EbayDuration: "DAYS_3" | "DAYS_5" | "DAYS_7" | "DAYS_10" | "DAYS_30" | "GTC";
        /**
         * EbayExportRequest
         * @description Schema for eBay export request
         */
        EbayExportRequest: {
            /**
             * Item Ids
             * @description List of WHIS item IDs to export
             */
            item_ids: string[];
            /** @description Default fields for all items */
            default_fields?: components["schemas"]["EbayFields"] | null;
        };
        /**
         * EbayFields
         * @description Schema for eBay-specific fields stored in item.custom_fields
         */
        EbayFields: {
            /**
             * Category Id
             * @description eBay category ID
             */
            category_id?: string | null;
            /** @description Item condition */
            condition?: components["schemas"]["EbayCondition"] | null;
            /** @description Listing format (auction/fixed) */
            listing_format?: components["schemas"]["EbayListingFormat"] | null;
            /** @description Listing duration */
            duration?: components["schemas"]["EbayDuration"] | null;
            /** @description Shipping service */
            shipping_service?: components["schemas"]["EbayShippingService"] | null;
            /**
             * Shipping Cost
             * @description Shipping cost
             */
            shipping_cost?: number | null;
            /**
             * Returns Accepted
             * @description Whether returns are accepted
             */
            returns_accepted?: boolean | null;
            /** @description Return period */
            return_period?: components["schemas"]["EbayReturnPeriod"] | null;
            /**
             * Payment Methods
             * @description Accepted payment methods
             */
            payment_methods?: components["schemas"]["EbayPaymentMethod"][] | null;
            /**
             * Starting Price
             * @description Starting price for auctions
             */
            starting_price?: number | null;
            /**
             * Reserve Price
             * @description Reserve price for auctions
             */
            reserve_price?: number | null;
            /**
             * Buy It Now Price
             * @description Buy It Now price
             */
            buy_it_now_price?: number | null;
            /**
             * Quantity
             * @description Number of items to list
             * @default 1
             */
            quantity?: number | null;
            /**
             * Domestic Shipping Only
             * @description Ship only within country
             * @default true
             */
            domestic_shipping_only?: boolean | null;
            /**
             * Item Specifics
             * @description Additional item specifics
             */
            item_specifics?: {
                [key: string]: string;
            } | null;
        };
        /**
         * EbayListingFormat
         * @enum {string}
         */
        EbayListingFormat: "FIXED_PRICE" | "AUCTION";
        /**
         * EbayPaymentMethod
         * @enum {string}
         */
        EbayPaymentMethod: "PAYPAL" | "CREDIT_CARD" | "BANK_TRANSFER";
        /**
         * EbayReturnPeriod
         * @enum {string}
         */
        EbayReturnPeriod: "DAYS_30" | "DAYS_60" | "NO_RETURNS";
        /**
         * EbayShippingService
         * @enum {string}
         */
        EbayShippingService: "USPS_FIRST_CLASS" | "USPS_PRIORITY" | "USPS_GROUND" | "UPS_GROUND" | "FEDEX_GROUND" | "FREIGHT" | "LOCAL_PICKUP";
        /** Error */
        Error: {
            /** Detail */
            detail: string;
        };
        /**
         * FbAvailability
         * @enum {string}
         */
        FbAvailability: "in stock" | "out of stock";
        /** FbCatalogExportRequest */
        FbCatalogExportRequest: {
            /**
             * Item Ids
             * @description WHIS item IDs to include
             */
            item_ids: string[];
            /** @description Default FB fields applied when an item lacks its own */
            default_fields?: components["schemas"]["FbFields"] | null;
        };
        /**
         * FbCondition
         * @description FB Marketplace's condition taxonomy.
         *
         *     FB uses a coarser grid than eBay. We map our own conditions to the
         *     FB values at copy-paste/CSV-generation time rather than requiring
         *     users to re-enter the same information under two keys.
         * @enum {string}
         */
        FbCondition: "NEW" | "USED_LIKE_NEW" | "USED_GOOD" | "USED_FAIR";
        /**
         * FbCopyPasteBlock
         * @description Server-rendered copy-paste bundle for the FB web form.
         *
         *     The frontend copies ``block`` to the clipboard and pulls the ZIP
         *     from ``images_zip_url`` when the user wants to upload images.
         */
        FbCopyPasteBlock: {
            /**
             * Title
             * @description FB-compliant title (≤100 chars)
             */
            title: string;
            /**
             * Description
             * @description Full listing description
             */
            description: string;
            /**
             * Price
             * @description Listing price
             */
            price?: number | null;
            /**
             * Suggested Category
             * @description Suggested FB category string
             */
            suggested_category?: string | null;
            /**
             * Tags
             * @description Keyword tags
             */
            tags?: string[];
            /**
             * Block
             * @description Full rendered text block ready for clipboard paste
             */
            block: string;
        };
        /**
         * FbFields
         * @description Facebook-specific fields stored in ``item.custom_fields.facebook``.
         */
        FbFields: {
            /**
             * Price
             * @description Listing price, USD
             */
            price?: number | null;
            /** @description FB condition */
            condition?: components["schemas"]["FbCondition"] | null;
            /**
             * Category
             * @description Free-form FB Marketplace category name (e.g. 'Electronics', 'Home Goods'). No canonical ID scheme like eBay — FB uses strings.
             */
            category?: string | null;
            /**
             * @description Stock state
             * @default in stock
             */
            availability?: components["schemas"]["FbAvailability"] | null;
            /**
             * Description Override
             * @description If set, replaces the item's main description when rendering the copy-paste block / catalog row. Use when the marketplace-facing description differs from the private inventory note.
             */
            description_override?: string | null;
            /**
             * Item Specifics
             * @description Marketplace-specific key/value metadata
             */
            item_specifics?: {
                [key: string]: string;
            } | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** ImportResult */
        ImportResult: {
            /** Success */
            success: boolean;
            /** Message */
            message: string;
            /** Items Imported */
            items_imported: number;
            /** Errors */
            errors?: string[] | null;
        };
        /** Item */
        Item: {
            /** Name */
            name: string;
            /** Category */
            category: string;
            /** Location */
            location: string;
            /** Brand */
            brand?: string | null;
            /** Model Number */
            model_number?: string | null;
            /** Serial Number */
            serial_number?: string | null;
            /** Barcode */
            barcode?: string | null;
            /** Purchase Date */
            purchase_date?: string | null;
            /** Purchase Price */
            purchase_price?: number | null;
            /** Current Value */
            current_value?: number | null;
            /** Warranty Expiration */
            warranty_expiration?: string | null;
            /** Notes */
            notes?: string | null;
            /** Custom Fields */
            custom_fields?: {
                [key: string]: unknown;
            } | null;
            /**
             * Id
             * Format: uuid4
             */
            id: string;
            /**
             * Owner Id
             * Format: uuid4
             */
            owner_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Images
             * @default []
             */
            images?: components["schemas"]["ItemImage"][];
            /** Estimated Value Low */
            estimated_value_low?: number | null;
            /** Estimated Value Median */
            estimated_value_median?: number | null;
            /** Estimated Value High */
            estimated_value_high?: number | null;
            /** Price Last Checked */
            price_last_checked?: string | null;
            /** Price Provider */
            price_provider?: string | null;
        };
        /** ItemCreate */
        ItemCreate: {
            /** Name */
            name: string;
            /** Category */
            category: string;
            /** Location */
            location: string;
            /** Brand */
            brand?: string | null;
            /** Model Number */
            model_number?: string | null;
            /** Serial Number */
            serial_number?: string | null;
            /** Barcode */
            barcode?: string | null;
            /** Purchase Date */
            purchase_date?: string | null;
            /** Purchase Price */
            purchase_price?: number | null;
            /** Current Value */
            current_value?: number | null;
            /** Warranty Expiration */
            warranty_expiration?: string | null;
            /** Notes */
            notes?: string | null;
            custom_fields?: components["schemas"]["CustomFieldsSchema"] | null;
        };
        /** ItemImage */
        ItemImage: {
            /**
             * Id
             * Format: uuid4
             */
            id: string;
            /**
             * Item Id
             * Format: uuid4
             */
            item_id: string;
            /** Filename */
            filename: string;
            /** File Path */
            file_path: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Thumbnail Path */
            thumbnail_path?: string | null;
            /** Thumbnail Generated At */
            thumbnail_generated_at?: string | null;
        };
        /** ItemList */
        ItemList: {
            /** Items */
            items: components["schemas"]["Item"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** ItemUpdate */
        ItemUpdate: {
            /** Name */
            name?: string | null;
            /** Category */
            category?: string | null;
            /** Location */
            location?: string | null;
            /** Brand */
            brand?: string | null;
            /** Model Number */
            model_number?: string | null;
            /** Serial Number */
            serial_number?: string | null;
            /** Barcode */
            barcode?: string | null;
            /** Purchase Date */
            purchase_date?: string | null;
            /** Purchase Price */
            purchase_price?: number | null;
            /** Current Value */
            current_value?: number | null;
            /** Warranty Expiration */
            warranty_expiration?: string | null;
            /** Notes */
            notes?: string | null;
            custom_fields?: components["schemas"]["CustomFieldsSchema"] | null;
        };
        /**
         * JobDetail
         * @description Response shape of GET /api/jobs/{job_id}.
         */
        JobDetail: {
            /** Job Id */
            job_id: string;
            status: components["schemas"]["JobStatus"];
            /** Result */
            result?: {
                [key: string]: unknown;
            } | null;
            /** Error */
            error?: string | null;
            /** Queued At */
            queued_at?: string | null;
            /** Started At */
            started_at?: string | null;
            /** Finished At */
            finished_at?: string | null;
        };
        /**
         * JobReference
         * @description Discriminator body returned when an endpoint enqueues a job.
         *
         *     The ``kind`` literal lets endpoints return a union type like
         *     ``JobReference | Backup`` and have the frontend branch on one
         *     field. When the sync-fallback path fires, the endpoint returns
         *     the full resource instead and the ``kind`` discriminator is
         *     missing.
         */
        JobReference: {
            /**
             * Kind
             * @default job
             * @constant
             */
            kind?: "job";
            /** Job Id */
            job_id: string;
        };
        /**
         * JobStatus
         * @description Finite state machine for an ARQ job as the frontend sees it.
         *
         *     Maps roughly onto ARQ's internal states (``deferred`` / ``queued``
         *     collapse to ``queued``; ``in_progress`` is ``running``;
         *     ``complete``/``failed`` are terminal).
         * @enum {string}
         */
        JobStatus: "queued" | "running" | "complete" | "failed" | "not_found";
        /**
         * RestoreRequest
         * @description Body schema for POST /backups/{id}/restore when committing a restore.
         *
         *     When ``dry_run=true`` is set on the query string the body is ignored and a
         *     preview is returned instead. When ``dry_run=false`` (or omitted) the caller
         *     MUST provide ``confirm_item_count`` that matches the current server-side
         *     count of their items; a mismatch is rejected with 409 to guard against
         *     accidental data loss from a stale UI.
         */
        RestoreRequest: {
            /** Confirm Item Count */
            confirm_item_count?: number | null;
        };
        /** RestoreResponse */
        RestoreResponse: {
            /** Success */
            success: boolean;
            /** Message */
            message: string;
            /** Items Restored */
            items_restored?: number | null;
            /** Images Restored */
            images_restored?: number | null;
            /** Errors */
            errors?: string[] | null;
            /**
             * Dry Run
             * @default false
             */
            dry_run?: boolean;
            /** Current Item Count */
            current_item_count?: number | null;
            /** Backup Item Count */
            backup_item_count?: number | null;
            /** Backup Image Count */
            backup_image_count?: number | null;
        };
        /** Token */
        Token: {
            /** Access Token */
            access_token: string;
            /** Token Type */
            token_type: string;
        };
        /** User */
        User: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Username */
            username: string;
            /**
             * Id
             * Format: uuid4
             */
            id: string;
            /** Is Active */
            is_active: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** UserCreate */
        UserCreate: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Username */
            username: string;
            /** Password */
            password: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * VisionResult
         * @description Full wrapper returned by ``VisionService.identify``.
         *
         *     Carries the raw suggestion plus the bookkeeping the UI + billing
         *     layer need (provider, model, prompt version, token usage, cost).
         *     The frontend polls ``GET /api/jobs/{id}`` and receives this
         *     shape under ``result`` once the task is complete.
         */
        VisionResult: {
            suggestion: components["schemas"]["VisionSuggestion"];
            /**
             * Provider
             * @description Configured LLM provider identifier (derived from base URL).
             */
            provider: string;
            /**
             * Model
             * @description Model name used for the vision call.
             */
            model: string;
            /**
             * Prompt Version
             * @description PROMPT_VERSION at call time, for A/B tracking.
             */
            prompt_version: string;
            /**
             * Tokens In
             * @default 0
             */
            tokens_in?: number;
            /**
             * Tokens Out
             * @default 0
             */
            tokens_out?: number;
            /**
             * Cost Usd Estimate
             * @default 0
             */
            cost_usd_estimate?: number;
            /**
             * Queried At
             * Format: date-time
             */
            queried_at: string;
        };
        /**
         * VisionSuggestion
         * @description Structured metadata inferred from one or more photos of an item.
         *
         *     Every field is ``Optional`` so the model can leave a slot blank
         *     when it's genuinely uncertain — forcing it to hallucinate a
         *     serial number when it can't read the label is exactly the
         *     failure mode this feature should avoid. The UI surfaces
         *     ``confidence`` + ``warnings`` so the user can decide what to
         *     accept.
         */
        VisionSuggestion: {
            /**
             * Name
             * @description Short, search-friendly item name. Prefer canonical names over marketing slogans.
             */
            name?: string | null;
            /**
             * Category
             * @description High-level category (Electronics, Tools, Kitchen, etc.). One noun or phrase.
             */
            category?: string | null;
            /**
             * Description
             * @description One or two sentences describing the item. Factual; no purple prose.
             */
            description?: string | null;
            /**
             * Brand
             * @description Manufacturer brand name as printed on the item.
             */
            brand?: string | null;
            /**
             * Model Number
             * @description Model / part number when visible on the item or label.
             */
            model_number?: string | null;
            /**
             * Serial Number
             * @description Serial number only when clearly visible. NEVER guess.
             */
            serial_number?: string | null;
            /**
             * Condition
             * @description Physical condition: NEW, LIKE_NEW, GOOD, ACCEPTABLE, FOR_PARTS.
             */
            condition?: string | null;
            /**
             * Year
             * @description Model / release year when inferable from the item.
             */
            year?: number | null;
            /**
             * Color
             * @description Dominant color.
             */
            color?: string | null;
            /**
             * Dimensions
             * @description Rough dimensions in the form 'WxDxH in cm' or 'diameter X cm'. Omit if not visible.
             */
            dimensions?: string | null;
            /**
             * Suggested Tags
             * @description Short keyword tags (≤5 words each) to aid later search.
             */
            suggested_tags?: string[];
            /**
             * Ebay Item Specifics
             * @description Flat key→value map aligned to eBay's Item Specifics fields for this category.
             */
            ebay_item_specifics?: {
                [key: string]: string;
            };
            /**
             * Fb Item Specifics
             * @description Flat key→value map aligned to Facebook Marketplace's item attributes.
             */
            fb_item_specifics?: {
                [key: string]: string;
            };
            /**
             * Confidence
             * @description Overall confidence in the suggestion, 0..1. Lower when photo quality is poor or the item is unrecognized.
             */
            confidence: number;
            /**
             * Warnings
             * @description Human-readable notes about uncertainty (e.g. 'Serial obscured', 'Multiple items in frame').
             */
            warnings?: string[];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    preflight_handler__rest_of_path__options: {
        parameters: {
            query: {
                request: unknown;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    register_user_api_register_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_for_access_token_api_token_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/x-www-form-urlencoded": components["schemas"]["Body_login_for_access_token_api_token_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Token"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_users_me_api_users_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    create_item_api_items__post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ItemCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Item"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_items_api_items_get: {
        parameters: {
            query?: {
                query?: string | null;
                category?: string | null;
                location?: string | null;
                min_value?: number | null;
                max_value?: number | null;
                sort_by?: string | null;
                sort_desc?: boolean | null;
                page?: number | null;
                page_size?: number | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ItemList"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_items_api_items_export_data_get: {
        parameters: {
            query: {
                /** @description Export format (csv or json) */
                format: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lookup_by_barcode_api_items_barcode__barcode__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                barcode: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Item"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_item_api_items__item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Item"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_item_api_items__item_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ItemUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Item"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_item_api_items__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bulk_delete_items_api_items_bulk_delete_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BulkDeleteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_categories_api_categories_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string[];
                };
            };
        };
    };
    get_locations_api_locations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string[];
                };
            };
        };
    };
    import_items_api_items_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_items_api_items_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_item_images_api_items__item_id__images_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ItemImage"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_item_image_api_items__item_id__images_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_item_image_api_items__item_id__images_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ItemImage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_image_api_images__image_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_value_by_category_api_analytics_value_by_category_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    }[];
                };
            };
        };
    };
    get_value_by_location_api_analytics_value_by_location_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    }[];
                };
            };
        };
    };
    get_value_trends_api_analytics_value_trends_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    get_warranty_status_api_analytics_warranty_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    get_age_analysis_api_analytics_age_analysis_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    list_backups_api_backups_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackupList"];
                };
            };
        };
    };
    create_backup_api_backups_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobReference"] | components["schemas"]["Backup"];
                };
            };
        };
    };
    restore_backup_api_backups__backup_id__restore_post: {
        parameters: {
            query?: {
                /** @description When true (the default), return a non-destructive preview describing what would be restored. When false the caller MUST supply confirm_item_count in the body, matching the server-side item count. */
                dry_run?: boolean;
            };
            header?: never;
            path: {
                backup_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["RestoreRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobReference"] | components["schemas"]["RestoreResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_backup_api_backups_upload_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_backup_api_backups_upload_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_backup_api_backups__backup_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                backup_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_backup_api_backups__backup_id__download_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                backup_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_categories_api_ebay_categories_get: {
        parameters: {
            query?: {
                item_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EbayCategoryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_to_ebay_api_ebay_export_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EbayExportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_ebay_fields_api_ebay_items__item_id__ebay_fields_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EbayFields"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EbayFields"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_categories_api_facebook_categories_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    update_fb_fields_api_facebook_items__item_id__fb_fields_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FbFields"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FbFields"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_copy_paste_block_api_facebook_items__item_id__copy_paste_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FbCopyPasteBlock"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_images_zip_api_facebook_items__item_id__images_zip_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_catalog_csv_api_facebook_export_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FbCatalogExportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_job_api_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    identify_item_api_vision_identify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_identify_item_api_vision_identify_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobReference"] | components["schemas"]["VisionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_check_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
}
