import AppLayout from "../components/layout/AppLayout";
import SignatureVerificationForm from "../components/SignatureVerification";

function SignatureVerification() {

  return (

    <AppLayout
      title="Signature Verification"
      subtitle="Siamese Neural Network signature authentication"
    >

      <SignatureVerificationForm />

    </AppLayout>

  );

}

export default SignatureVerification;
