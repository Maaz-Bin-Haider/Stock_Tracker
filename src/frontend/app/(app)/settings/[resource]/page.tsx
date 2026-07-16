"use client";

import { useParams } from "next/navigation";

import ResourceCrud, { type ColumnDef, type FieldDef } from "@/components/resource-crud";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

const RESOURCES: Record<
  string,
  { title: string; endpoint: string; columns: ColumnDef[]; fields: FieldDef[] }
> = {
  categories: {
    title: "Categories",
    endpoint: "/api/v1/categories/",
    columns: [
      { key: "name", label: "Name" },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      { name: "name", label: "Name", required: true },
      { name: "is_active", label: "Active", type: "checkbox" },
    ],
  },
  locations: {
    title: "Locations",
    endpoint: "/api/v1/locations/",
    columns: [
      { key: "name", label: "Name" },
      { key: "country", label: "Country" },
      { key: "city", label: "City" },
      { key: "can_purchase", label: "Purchases" },
      { key: "is_sales_location", label: "Sales" },
      { key: "region_group", label: "Region" },
      { key: "gst_region", label: "GST Region" },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      { name: "name", label: "Name", required: true },
      { name: "country", label: "Country" },
      { name: "city", label: "City" },
      { name: "can_purchase", label: "Can purchase", type: "checkbox" },
      { name: "is_sales_location", label: "Sales location", type: "checkbox", defaultValue: false },
      { name: "region_group", label: "Region group (e.g. AU)" },
      { name: "gst_region", label: "GST region (e.g. AU, NZ)" },
      { name: "is_active", label: "Active", type: "checkbox" },
    ],
  },
  currencies: {
    title: "Currencies",
    endpoint: "/api/v1/currencies/",
    columns: [
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      { name: "code", label: "Code", required: true },
      { name: "name", label: "Name" },
      { name: "is_active", label: "Active", type: "checkbox" },
    ],
  },
  "exchange-rates": {
    title: "Exchange Rates",
    endpoint: "/api/v1/exchange-rates/",
    columns: [
      { key: "currency_code", label: "Currency" },
      { key: "rate_to_aed", label: "Rate to AED" },
      { key: "effective_date", label: "Effective" },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      {
        name: "currency",
        label: "Currency",
        required: true,
        optionsEndpoint: "/api/v1/currencies/",
        optionLabelKey: "code",
      },
      { name: "rate_to_aed", label: "Rate to AED", type: "number", required: true },
      { name: "effective_date", label: "Effective date", type: "date", required: true },
      { name: "is_active", label: "Active", type: "checkbox" },
    ],
  },
  "gst-rates": {
    title: "GST Rates",
    endpoint: "/api/v1/gst-rates/",
    columns: [
      { key: "location_name", label: "Location" },
      { key: "rate", label: "Rate %" },
      { key: "effective_from", label: "From" },
      { key: "effective_to", label: "To" },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      {
        name: "location",
        label: "Location",
        required: true,
        optionsEndpoint: "/api/v1/locations/",
      },
      { name: "rate", label: "Rate (%)", type: "number", required: true },
      { name: "effective_from", label: "Effective from", type: "date", required: true },
      { name: "effective_to", label: "Effective to", type: "date" },
      { name: "is_active", label: "Active", type: "checkbox" },
    ],
  },
};

export default function SettingsResourcePage() {
  const user = useAuth();
  const params = useParams<{ resource: string }>();
  const config = RESOURCES[params.resource];

  if (!config) {
    return <p className="text-sm text-muted">Unknown settings page.</p>;
  }

  return (
    <ResourceCrud
      key={params.resource}
      title={config.title}
      endpoint={config.endpoint}
      columns={config.columns}
      fields={config.fields}
      canWrite={canWrite(user?.role, params.resource)}
    />
  );
}
