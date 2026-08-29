import AppLayout from "../components/layout/AppLayout";
import SignatureVerificationForm from "../components/SignatureVerification";

function SignatureVerification() {

  return (

    <AppLayout
      title="Signature Analysis"
      subtitle="Identity and handwritten signature examination"
    >

      <SignatureVerificationForm />

    </AppLayout>

  );

}

export default SignatureVerification;
