"use client";

import { FormEvent, useRef, useState } from "react";
import { Camera, Check, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field, Input, Textarea } from "@/components/ui/Input";
import { createEntry, uploadPhoto } from "@/lib/sessions";
import { apiErrorMessage } from "@/lib/api";

const VEHICLE_TYPES = ["Open Body", "Container", "Tanker", "Trailer", "Mini Truck", "Other"];

export function TruckEntryForm() {
  const [truckNumber, setTruckNumber] = useState("");
  const [driverMobile, setDriverMobile] = useState("");
  const [driverName, setDriverName] = useState("");
  const [company, setCompany] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [remarks, setRemarks] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetForm() {
    setTruckNumber("");
    setDriverMobile("");
    setDriverName("");
    setCompany("");
    setVehicleType("");
    setRemarks("");
    setPhotoFile(null);
    setPhotoPreview(null);
  }

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      let entry_photo_url: string | undefined;
      if (photoFile) {
        entry_photo_url = await uploadPhoto(photoFile);
      }
      await createEntry({
        truck_number: truckNumber,
        driver_mobile: driverMobile,
        driver_name: driverName || undefined,
        transport_company: company || undefined,
        vehicle_type: vehicleType || undefined,
        remarks: remarks || undefined,
        entry_photo_url,
      });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        resetForm();
      }, 2200);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save entry. Try again."));
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center rounded-lg bg-ok-light text-ok">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-ok text-white">
          <Check size={40} strokeWidth={3} />
        </div>
        <p className="mt-4 text-xl font-bold">Entry Saved</p>
        <p className="text-sm text-ok/80">{truckNumber} marked as inside</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Truck Number" required>
        <Input
          value={truckNumber}
          onChange={(e) => setTruckNumber(e.target.value.toUpperCase())}
          placeholder="e.g. TN37AB1234"
          className="plate text-lg uppercase"
          autoFocus
          required
        />
      </Field>

      <Field label="Driver Mobile" required>
        <Input
          type="tel"
          inputMode="numeric"
          value={driverMobile}
          onChange={(e) => setDriverMobile(e.target.value)}
          placeholder="10-digit mobile number"
          required
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Driver Name">
          <Input value={driverName} onChange={(e) => setDriverName(e.target.value)} placeholder="Optional" />
        </Field>
        <Field label="Vehicle Type">
          <select
            value={vehicleType}
            onChange={(e) => setVehicleType(e.target.value)}
            className="input"
          >
            <option value="">Select</option>
            {VEHICLE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Transport Company">
        <Input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Optional" />
      </Field>

      <Field label="Remarks">
        <Textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} placeholder="Optional notes" />
      </Field>

      <div>
        <span className="mb-1.5 block text-sm font-medium text-yard-700">Entry Photo</span>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handlePhotoChange}
          className="hidden"
        />
        {photoPreview ? (
          <div className="relative">
            <img src={photoPreview} alt="Truck entry" className="h-40 w-full rounded-lg object-cover" />
            <button
              type="button"
              onClick={() => {
                setPhotoFile(null);
                setPhotoPreview(null);
              }}
              className="absolute right-2 top-2 rounded-full bg-yard-900/80 p-1.5 text-white"
            >
              <X size={16} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex h-28 w-full flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-yard-100 text-yard-500"
          >
            <Camera size={24} />
            <span className="text-sm">Tap to capture photo</span>
          </button>
        )}
      </div>

      {error && <p className="rounded bg-warn-light px-3 py-2 text-sm text-warn">{error}</p>}

      <Button type="submit" size="lg" className="w-full" loading={submitting}>
        Save Entry
      </Button>
    </form>
  );
}
