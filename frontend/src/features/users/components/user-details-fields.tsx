import { useFormContext } from "react-hook-form";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { AGE_MAX, AGE_MIN, type EditUserValues } from "../schemas";
import { RoleOptions } from "./role-options";

type UserDetailsFieldsProps = { idPrefix: string; currentRole?: string };

// Name, phone, age, and role inputs shared by the create and edit forms.
export function UserDetailsFields({ idPrefix, currentRole }: UserDetailsFieldsProps) {
  const {
    register,
    formState: { errors },
  } = useFormContext<EditUserValues>();
  const id = (name: string) => `${idPrefix}-${name}`;
  return (
    <>
      <Field id={id("name")} label="Name" error={errors.name?.message}>
        <Input autoComplete="off" {...fieldAria(id("name"), errors.name?.message)} {...register("name")} />
      </Field>
      <Field id={id("phone")} label="Phone" error={errors.phone?.message} hint="Required for technicians.">
        <Input type="tel" autoComplete="off" {...fieldAria(id("phone"), errors.phone?.message, true)} {...register("phone")} />
      </Field>
      <Field id={id("age")} label="Age" error={errors.age?.message} hint={`Between ${AGE_MIN} and ${AGE_MAX}, optional.`}>
        <Input inputMode="numeric" autoComplete="off" {...fieldAria(id("age"), errors.age?.message, true)} {...register("age")} />
      </Field>
      <Field id={id("role")} label="Role" error={errors.roleCode?.message}>
        <Select {...fieldAria(id("role"), errors.roleCode?.message)} {...register("roleCode")}>
          <RoleOptions current={currentRole} />
        </Select>
      </Field>
    </>
  );
}
