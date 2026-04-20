import { z } from 'zod';

// HTML <input type="number"> + <input type="date"> always produce strings.
// The schema accepts strings and transforms them at parse time — empty
// string becomes undefined (so the backend treats it as "not set") and
// non-empty strings become numbers / ISO-date strings respectively.
//
// NOTE: no ``.default()`` on any field. react-hook-form always provides
// a value (via ``defaultValues``), so making the schema's input-side
// fields ``| undefined`` would just confuse the Resolver type.
const optionalFloat = z
  .string()
  .transform((v) => (v === '' ? undefined : Number(v)))
  .refine((v) => v === undefined || (!Number.isNaN(v) && v >= 0), {
    message: 'Must be a non-negative number',
  });

const optionalDate = z
  .string()
  .transform((v) => (v === '' ? undefined : v));

export const addItemSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  category: z.string().min(1, 'Category is required'),
  location: z.string().min(1, 'Location is required'),
  brand: z.string(),
  model_number: z.string(),
  serial_number: z.string(),
  barcode: z.string(),
  purchase_date: optionalDate,
  purchase_price: optionalFloat,
  current_value: optionalFloat,
  warranty_expiration: optionalDate,
  notes: z.string(),
  custom_fields: z.record(z.string(), z.unknown()),
});

// Raw form values before zod transforms run — what the <input>s produce.
export interface AddItemFormValues {
  name: string;
  category: string;
  location: string;
  brand: string;
  model_number: string;
  serial_number: string;
  barcode: string;
  purchase_date: string;
  purchase_price: string;
  current_value: string;
  warranty_expiration: string;
  notes: string;
  custom_fields: Record<string, unknown>;
}

export type AddItemSubmitValues = z.infer<typeof addItemSchema>;

export const addItemDefaults: AddItemFormValues = {
  name: '',
  category: '',
  location: '',
  brand: '',
  model_number: '',
  serial_number: '',
  barcode: '',
  purchase_date: '',
  purchase_price: '',
  current_value: '',
  warranty_expiration: '',
  notes: '',
  custom_fields: {},
};
