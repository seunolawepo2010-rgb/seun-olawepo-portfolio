import { useState } from "react";
import { toast } from "sonner";
import { Send } from "lucide-react";
import { api, errMsg } from "../lib/api";

const input = "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20";

export function ContactForm() {
  const [v, setV] = useState({ name: "", email: "", company: "", message: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/contact", v);
      setSent(true);
      toast.success("Message sent. Thank you!");
      setV({ name: "", email: "", company: "", message: "" });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });
  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2" data-testid="contact-form">
      <input required minLength={2} placeholder="Your name" className={input} value={v.name} onChange={set("name")} data-testid="contact-name" aria-label="Name" />
      <input required type="email" placeholder="Work email" className={input} value={v.email} onChange={set("email")} data-testid="contact-email" aria-label="Email" />
      <input placeholder="Company (optional)" className={`${input} sm:col-span-2`} value={v.company} onChange={set("company")} data-testid="contact-company" aria-label="Company" />
      <textarea required minLength={10} rows={5} placeholder="How can I help? (role, team, timeline)" className={`${input} sm:col-span-2`} value={v.message} onChange={set("message")} data-testid="contact-message" aria-label="Message" />
      <button disabled={busy} className="inline-flex w-fit items-center gap-2 rounded-md bg-teal-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60" data-testid="contact-submit"><Send className="h-4 w-4" />{busy ? "Sending…" : "Send message"}</button>
      {sent && <p className="text-sm text-emerald-700 sm:col-span-2" data-testid="contact-success">Thanks — your message was delivered to my inbox.</p>}
    </form>
  );
}
