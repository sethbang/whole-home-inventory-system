/**
 * "Marketplace Integrations" section extracted from ItemDetail (b-plus-to-a
 * refactor). Wraps the eBay + Facebook integration panels in a headlessui
 * ``Tab.Group``. The caller owns all state and mutations — this component is
 * a thin presentational shell that wires the field values and handlers into
 * the tabbed panels.
 *
 * The ``Tab.List`` is associated with the section heading via
 * ``aria-labelledby`` so screen-reader users get context for the tabs.
 */

import { useId, useState } from 'react';
import { Tab } from '@headlessui/react';

import EbayFields, { EbayFieldsData } from './EbayFields';
import FacebookFields from './FacebookFields';
import FacebookCopyPasteDialog from './FacebookCopyPasteDialog';
import type { FbFieldsData } from '../api/types';

interface MarketplacePanelsProps {
  itemId: string;
  ebayFields: EbayFieldsData;
  fbFields: FbFieldsData;
  fbCategories: string[];
  onEbayChange: (fields: EbayFieldsData) => void;
  onFbChange: (fields: FbFieldsData) => void;
  onEbayCategoryLookup: () => void;
}

export default function MarketplacePanels({
  itemId,
  ebayFields,
  fbFields,
  fbCategories,
  onEbayChange,
  onFbChange,
  onEbayCategoryLookup,
}: MarketplacePanelsProps) {
  const [showFbDialog, setShowFbDialog] = useState(false);
  const headingId = useId();

  return (
    <div className="sm:col-span-6 pt-8">
      <h3
        id={headingId}
        className="text-lg font-medium leading-6 text-fg mb-4"
      >
        Marketplace Integrations
      </h3>
      <Tab.Group>
        <Tab.List
          aria-labelledby={headingId}
          className="flex gap-2 border-b border-line"
        >
          {['eBay', 'Facebook Marketplace'].map((label) => (
            <Tab
              key={label}
              className={({ selected }) =>
                `px-4 py-2 text-sm font-medium border-b-2 focus:outline-none ${
                  selected
                    ? 'border-primary text-primary-hover'
                    : 'border-transparent text-subtle hover:text-muted'
                }`
              }
            >
              {label}
            </Tab>
          ))}
        </Tab.List>
        <Tab.Panels className="mt-6">
          <Tab.Panel>
            <EbayFields
              fields={ebayFields}
              onChange={onEbayChange}
              onCategoryLookup={onEbayCategoryLookup}
            />
          </Tab.Panel>
          <Tab.Panel>
            <FacebookFields
              fields={fbFields}
              categories={fbCategories}
              onChange={onFbChange}
            />
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setShowFbDialog(true)}
                className="rounded-md border border-transparent bg-primary px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-primary-hover"
              >
                Generate copy-paste block
              </button>
            </div>
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>

      {showFbDialog && (
        <FacebookCopyPasteDialog
          itemId={itemId}
          onClose={() => setShowFbDialog(false)}
        />
      )}
    </div>
  );
}
