"use client";

import ResourceCrud from "@/components/resource-crud";
import { useAuth } from "@/lib/auth";

const ROLE_OPTIONS = [
  { value: "ADMIN", label: "Admin" },
  { value: "PURCHASE", label: "Purchase User" },
  { value: "SALE", label: "Sale User" },
  { value: "VIEWER", label: "Viewer" },
];

export default function UsersPage() {
  const user = useAuth();

  return (
    <ResourceCrud
      title="Users"
      endpoint="/api/v1/users/"
      canWrite={user?.role === "ADMIN"}
      allowDelete={false}
      columns={[
        { key: "username", label: "Username" },
        { key: "email", label: "Email" },
        { key: "first_name", label: "First name" },
        { key: "last_name", label: "Last name" },
        { key: "role", label: "Role" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "username", label: "Username", required: true },
        { name: "email", label: "Email" },
        { name: "first_name", label: "First name" },
        { name: "last_name", label: "Last name" },
        { name: "role", label: "Role", type: "select", required: true, options: ROLE_OPTIONS },
        {
          name: "password",
          label: "Password (leave blank to keep current)",
          type: "password",
        },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}
