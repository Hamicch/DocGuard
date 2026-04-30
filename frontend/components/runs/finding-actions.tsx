"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { UniversalScreenLoader } from "@/components/ui/universal-screen-loader";
import { setFindingAction } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type FindingAction = "accepted" | "ignored" | "custom";

type Props = {
	findingId: string;
};

export function FindingActions({ findingId }: Props) {
	const [isPending, startTransition] = useTransition();
	const [error, setError] = useState<string | null>(null);
	const router = useRouter();

	const handleAction = (action: FindingAction) => {
		startTransition(async () => {
			setError(null);
			try {
				const supabase = createClient();
				const {
					data: { session },
				} = await supabase.auth.getSession();
				if (!session) {
					setError("Session expired. Please sign in again.");
					return;
				}

				let custom_fix: string | undefined;
				if (action === "custom") {
					custom_fix = window.prompt("Enter your custom fix suggestion:") ?? "";
					if (!custom_fix.trim()) {
						setError("Custom action requires a custom fix.");
						return;
					}
				}

				await setFindingAction(session.access_token, findingId, {
					action,
					custom_fix,
				});
				router.refresh();
			} catch (err) {
				setError(
					err instanceof Error
						? err.message
						: "Failed to update finding action.",
				);
			}
		});
	};

	return (
		<div className='mt-3 flex flex-wrap items-center gap-2'>
			{isPending ? (
				<UniversalScreenLoader
					variant='inline'
					message='Saving…'
					spinnerClassName='h-3.5 w-3.5'
					className='w-full basis-full sm:basis-auto sm:w-auto'
				/>
			) : null}
			<button
				type='button'
				onClick={() => handleAction("accepted")}
				disabled={isPending}
				className='rounded bg-green-600 px-3 py-1 text-xs text-white disabled:opacity-50'
			>
				Accept
			</button>
			<button
				type='button'
				onClick={() => handleAction("ignored")}
				disabled={isPending}
				className='rounded bg-gray-700 px-3 py-1 text-xs text-white disabled:opacity-50'
			>
				Ignore
			</button>
			<button
				type='button'
				onClick={() => handleAction("custom")}
				disabled={isPending}
				className='rounded border border-gray-300 px-3 py-1 text-xs disabled:opacity-50'
			>
				Custom
			</button>
			{error ? <p className='w-full text-xs text-red-600'>{error}</p> : null}
		</div>
	);
}
