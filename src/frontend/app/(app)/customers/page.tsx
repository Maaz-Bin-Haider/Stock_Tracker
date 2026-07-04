"use client";

import ResourceCrud from "@/components/resource-crud";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

export default function CustomersPage() {
  const user = useAuth();

  return (
    <ResourceCrud
      title="Customers"
      endpoint="/api/v1/customers/"
      canWrite={canWrite(user?.role, "customers")}
      columns={[
        { key: "name", label: "Name" },
        { key: "code", label: "Code" },
        { key: "phone", label: "Phone" },
        { key: "country", label: "Country" },
        { key: "city", label: "City" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "name", label: "Customer name", required: true },
        { name: "code", label: "Code" },
        { name: "phone", label: "Phone" },
        { name: "email", label: "Email" },
        { name: "country", label: "Country" },
        { name: "city", label: "City" },
        { name: "address", label: "Address", type: "textarea" },
        { name: "notes", label: "Notes", type: "textarea" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}
