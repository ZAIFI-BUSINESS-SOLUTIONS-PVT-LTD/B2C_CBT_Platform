
import { useEffect, useState } from "react";

export default function GoogleCallback() {
	const [message, setMessage] = useState<string>("Completing sign in...");

	useEffect(() => {
		const params = new URLSearchParams(window.location.search);
		const code = params.get("code");
		const state = params.get("state");
		const error = params.get("error");
		const errorDescription = params.get("error_description");

		const sendMessage = (payload: Record<string, any>) => {
			try {
				if (window.opener && !window.opener.closed) {
					window.opener.postMessage(payload, window.location.origin);
					setMessage("Sign-in completed. This window will close shortly.");
					// Give the opener a moment to handle the message before closing
					setTimeout(() => {
						window.close();
					}, 500);
				} else {
					// If no opener (user opened callback directly), persist the payload so the app can pick it up
					localStorage.setItem("google_auth_callback", JSON.stringify(payload));
					setMessage("Authentication data saved. Return to the app to complete sign-in.");
				}
			} catch (e) {
				// Fallback: show an error to the user
				// eslint-disable-next-line no-console
				console.error("Failed to postMessage to opener", e);
				setMessage("Authentication failed. Please close this window and try again.");
			}
		};

		if (error) {
			sendMessage({ type: "GOOGLE_AUTH_ERROR", error, error_description: errorDescription });
			return;
		}

		if (code) {
			sendMessage({ type: "GOOGLE_AUTH_SUCCESS", code, state });
			return;
		}

		// Some flows may return an id_token in the hash portion
		if (window.location.hash) {
			const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
			const idToken = hashParams.get("id_token");
			if (idToken) {
				sendMessage({ type: "GOOGLE_AUTH_SUCCESS", idToken });
				return;
			}
		}

		setMessage("No authentication data found in the callback URL.");
	}, []);

	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50">
			<div className="max-w-md w-full space-y-4 text-center">
				<div>
					<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
				</div>
				<h2 className="mt-4 text-xl font-medium text-gray-900">Completing sign in</h2>
				<p className="text-sm text-gray-600">{message}</p>
			</div>
		</div>
	);
}
