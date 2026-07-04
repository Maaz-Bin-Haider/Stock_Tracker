"use client";

import ResourceCrud from "@/components/resource-crud";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

export default function ProductsPage() {
  const user = useAuth();

  return (
    <ResourceCrud
      title="Products"
      endpoint="/api/v1/products/"
      canWrite={canWrite(user?.role, "products")}
      columns={[
        { key: "name", label: "Name" },
        { key: "storage_specs", label: "Storage/Specs" },
        { key: "category_name", label: "Category" },
        { key: "brand", label: "Brand" },
        { key: "model", label: "Model" },
        { key: "sku", label: "SKU" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "name", label: "Product name", required: true },
        { name: "storage_specs", label: "Storage/Specs" },
        {
          name: "category",
          label: "Category",
          required: true,
          optionsEndpoint: "/api/v1/categories/",
        },
        { name: "brand", label: "Brand" },
        { name: "model", label: "Model" },
        { name: "sku", label: "SKU" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}
