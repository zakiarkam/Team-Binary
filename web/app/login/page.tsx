import type { Metadata } from "next";

import { AuthShell, LoginForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Sign in — Marketing OS" };

export default function LoginPage() {
  return (
    <AuthShell
      title="Sign in"
      subtitle="Your website's visitors, segmented, campaigned and analysed."
    >
      <LoginForm />
    </AuthShell>
  );
}
