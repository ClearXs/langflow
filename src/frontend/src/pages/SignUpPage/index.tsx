import * as Form from "@radix-ui/react-form";
import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import LangflowLogo from "@/assets/LangflowLogo.svg?react";
import InputComponent from "@/components/core/parameterRenderComponent/components/inputComponent";
import { useAddUser } from "@/controllers/API/queries/auth";
import { CustomLink } from "@/customization/components/custom-link";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import { track } from "@/customization/utils/analytics";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { SIGNUP_ERROR_ALERT } from "../../constants/alerts_constants";
import { CONTROL_INPUT_STATE } from "../../constants/constants";
import useAlertStore from "../../stores/alertStore";
import type {
  inputHandlerEventType,
  signUpInputStateType,
  UserInputType,
} from "../../types/components";

export default function SignUp(): JSX.Element {
  const { t } = useTranslation();
  
  const [inputState, setInputState] =
    useState<signUpInputStateType>(CONTROL_INPUT_STATE);

  const [isDisabled, setDisableBtn] = useState<boolean>(true);

  const { password, cnfPassword, username } = inputState;
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const navigate = useCustomNavigate();

  const { mutate: mutateAddUser } = useAddUser();

  function handleInput({
    target: { name, value },
  }: inputHandlerEventType): void {
    setInputState((prev) => ({ ...prev, [name]: value }));
  }

  useEffect(() => {
    if (password !== cnfPassword) return setDisableBtn(true);
    if (password === "" || cnfPassword === "") return setDisableBtn(true);
    if (username === "") return setDisableBtn(true);
    setDisableBtn(false);
  }, [password, cnfPassword, username, handleInput]);

  function handleSignup(): void {
    const { username, password } = inputState;
    const newUser: UserInputType = {
      username: username.trim(),
      password: password.trim(),
    };

    mutateAddUser(newUser, {
      onSuccess: (user) => {
        track("User Signed Up", user);
        setSuccessData({
          title: t("constants.signup.success"),
        });
        navigate("/login");
      },
      onError: (error) => {
        const {
          response: {
            data: { detail },
          },
        } = error;
        setErrorData({
          title: SIGNUP_ERROR_ALERT,
          list: [detail],
        });
      },
    });
  }

  return (
    <Form.Root
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        if (password === "") {
          event.preventDefault();
          return;
        }

        const _data = Object.fromEntries(new FormData(event.currentTarget));
        event.preventDefault();
      }}
      className="h-screen w-full"
    >
      <div className="flex h-full w-full flex-col items-center justify-center bg-muted">
        <div className="flex w-72 flex-col items-center justify-center gap-2">
          <LangflowLogo
            title="Langflow logo"
            className="mb-4 h-10 w-10 scale-[1.5]"
          />
          <span className="mb-6 text-2xl font-semibold text-primary">
            {t("signUpPage.title")}
          </span>
          <div className="mb-3 w-full">
            <Form.Field name="username">
              <Form.Label className="data-[invalid]:label-invalid">
                {t("signUpPage.username")}{" "}
                <span className="font-medium text-destructive">
                  {t("signUpPage.required")}
                </span>
              </Form.Label>

              <Form.Control asChild>
                <Input
                  type="username"
                  onChange={({ target: { value } }) => {
                    handleInput({ target: { name: "username", value } });
                  }}
                  value={username}
                  className="w-full"
                  required
                  placeholder={t("signUpPage.usernamePlaceholder")}
                />
              </Form.Control>

              <Form.Message match="valueMissing" className="field-invalid">
                {t("signUpPage.usernameRequired")}
              </Form.Message>
            </Form.Field>
          </div>
          <div className="mb-3 w-full">
            <Form.Field name="password" serverInvalid={password != cnfPassword}>
              <Form.Label className="data-[invalid]:label-invalid">
                {t("signUpPage.password")}{" "}
                <span className="font-medium text-destructive">
                  {t("signUpPage.required")}
                </span>
              </Form.Label>
              <InputComponent
                onChange={(value) => {
                  handleInput({ target: { name: "password", value } });
                }}
                value={password}
                isForm
                password={true}
                required
                placeholder={t("signUpPage.passwordPlaceholder")}
                className="w-full"
              />

              <Form.Message className="field-invalid" match="valueMissing">
                {t("signUpPage.passwordRequired")}
              </Form.Message>

              {password != cnfPassword && (
                <Form.Message className="field-invalid">
                  {t("signUpPage.passwordsNotMatch")}
                </Form.Message>
              )}
            </Form.Field>
          </div>
          <div className="w-full">
            <Form.Field
              name="confirmpassword"
              serverInvalid={password != cnfPassword}
            >
              <Form.Label className="data-[invalid]:label-invalid">
                {t("signUpPage.confirmPassword")}{" "}
                <span className="font-medium text-destructive">
                  {t("signUpPage.required")}
                </span>
              </Form.Label>

              <InputComponent
                onChange={(value) => {
                  handleInput({ target: { name: "cnfPassword", value } });
                }}
                value={cnfPassword}
                isForm
                password={true}
                required
                placeholder={t("signUpPage.confirmPasswordPlaceholder")}
                className="w-full"
              />

              <Form.Message className="field-invalid" match="valueMissing">
                {t("signUpPage.confirmPasswordRequired")}
              </Form.Message>
            </Form.Field>
          </div>
          <div className="w-full">
            <Form.Submit asChild>
              <Button
                disabled={isDisabled}
                type="submit"
                className="mr-3 mt-6 w-full"
                onClick={() => {
                  handleSignup();
                }}
              >
                {t("signUpPage.signUpButton")}
              </Button>
            </Form.Submit>
          </div>
          <div className="w-full">
            <CustomLink to="/login">
              <Button className="w-full" variant="outline">
                {t("signUpPage.alreadyHaveAccount")}&nbsp;
                <b>{t("signUpPage.signIn")}</b>
              </Button>
            </CustomLink>
          </div>
        </div>
      </div>
    </Form.Root>
  );
}