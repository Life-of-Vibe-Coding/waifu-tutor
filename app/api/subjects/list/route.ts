import { NextResponse } from "next/server";
import { listSubjects } from "@/lib/subjects";
import { DEMO_USER_ID } from "@/lib/constants";

export async function GET() {
  const subjects = listSubjects(DEMO_USER_ID);
  return NextResponse.json(subjects);
}
