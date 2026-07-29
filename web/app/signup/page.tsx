import type { Metadata } from "next";

import { AuthShell, SignupForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Create account — Marketing OS" };

export default function SignupPage() {
  return (
    <AuthShell
      title="Create your company account"
      subtitle="Register your website, install one script tag, and its visitors become your marketing audience."
    >
      <SignupForm />
    </AuthShell>
  );
}
