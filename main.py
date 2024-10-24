from typing import Annotated, Literal

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Creatinine Clearance (CGE) Tool",
    description="Calculates Creatinine Clearance (CrCl) using the Cockcroft-Gault equation with unit system conversion and special considerations for overweight patients.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CrClFormInput(BaseModel):
    """Form-based input schema for calculating CrCl with unit conversion."""

    unit_system: Literal["metric", "imperial"] = Field(
        default="metric",
        title="Unit System",
        examples=["metric", "imperial"],
        description="Select your measurement system. Either 'metric' (kg, mg/dL) or 'imperial' (lbs, mg/dL).",
    )
    weight: float = Field(
        title="Weight",
        examples=[70.0],
        description="The patient's weight in kilograms (kg) if using metric, or pounds (lbs) if using imperial.",
        gt=0,
    )
    height: float = Field(
        title="Height",
        examples=[170.0],
        description="The patient's height in inches if using imperial, or centimeters if using metric.",
        gt=0,
    )
    age: int = Field(
        title="Age",
        examples=[45],
        description="The patient's age in years.",
        ge=18,
    )
    serum_creatinine: float = Field(
        title="Serum Creatinine",
        examples=[1.1],
        description="The serum creatinine level in mg/dL.",
        gt=0,
    )
    sex: Literal["male", "female"] = Field(
        title="Sex",
        examples=["male"],
        description="The biological sex of the patient. Either 'male' or 'female'.",
    )


class CrClFormOutput(BaseModel):
    """Form-based output schema for CrCl calculation results."""

    original_crcl: str = Field(
        title="Original CrCl",
        description="The calculated original creatinine clearance in mL/min.",
    )
    modified_crcl: str = Field(
        title="Modified CrCl for Overweight",
        description="The calculated creatinine clearance for overweight patients using Adjusted Body Weight (ABW).",
    )
    crcl_range: str = Field(
        title="CrCl Range Using IBW and ABW",
        description="The range of CrCl values using Ideal Body Weight (IBW) and Adjusted Body Weight (ABW).",
    )


def calculate_ibw(height_in_inches: float, sex: str) -> float:
    """Calculates Ideal Body Weight (IBW) based on height and sex."""
    if sex == "male":
        ibw = 50 + 2.3 * (height_in_inches - 60)  # Height in inches
    else:
        ibw = 45.5 + 2.3 * (height_in_inches - 60)  # Height in inches
    return ibw


@app.post(
    "/calculate_crcl/",
    response_model=CrClFormOutput,
    summary="Calculate Creatinine Clearance (CrCl) with considerations for overweight patients",
    description="Calculate the Creatinine Clearance (CrCl) using the Cockcroft-Gault equation and provide additional information for overweight patients using IBW and ABW.",
)
def calculate_crcl(
    data: Annotated[CrClFormInput, Form()],
) -> CrClFormOutput:
    """Calculate the CrCl and provide additional information for overweight patients using IBW and ABW.

    Args:
        data: CrClFormInput - input data containing patient's weight, age, serum creatinine, sex, and unit system.

    Returns:
        CrClFormOutput: calculated CrCl and additional info for overweight patients.
    """
    # Convert weight and height to metric if using imperial
    if data.unit_system == "imperial":
        weight_in_kg = data.weight * 0.453592  # Convert lbs to kg
        height_in_inches = data.height  # Height is already in inches
    else:
        weight_in_kg = data.weight  # Weight is already in kg
        height_in_inches = data.height / 2.54  # Convert height from cm to inches

    # Calculate Ideal Body Weight (IBW)
    ibw = calculate_ibw(height_in_inches, data.sex)

    # Adjusted Body Weight (ABW) for overweight patients
    if weight_in_kg > ibw:
        abw = ibw + 0.4 * (weight_in_kg - ibw)
    else:
        abw = weight_in_kg  # If the patient is not overweight, use actual body weight

    # Constants for male and female
    sex_factor = 0.85 if data.sex == "female" else 1.0

    # Original Cockcroft-Gault formula
    original_crcl = (
        (140 - data.age) * weight_in_kg * sex_factor / (72 * data.serum_creatinine)
    )

    # Modified Cockcroft-Gault formula using Adjusted Body Weight (ABW)
    modified_crcl = (
        (140 - data.age) * abw * sex_factor / (72 * data.serum_creatinine)
    )

    # CrCl using Ideal Body Weight (IBW)
    crcl_using_ibw = (
        (140 - data.age) * ibw * sex_factor / (72 * data.serum_creatinine)
    )

    # Round CrCl values to whole numbers
    original_crcl = round(original_crcl)
    modified_crcl = round(modified_crcl)
    crcl_using_ibw = round(crcl_using_ibw)

    # Prepare output
    crcl_range = f"{min(crcl_using_ibw, modified_crcl):.1f}-{max(crcl_using_ibw, modified_crcl):.1f} mL/min"

    return CrClFormOutput(
        original_crcl=f"{original_crcl} mL/min\nCreatinine clearance, original Cockcroft-Gault",
        modified_crcl=f"{modified_crcl} mL/min\nCreatinine clearance modified for overweight patient, using adjusted body weight of {round(abw, 1)} kg ({round(abw / 0.453592, 1)} lbs).",
        crcl_range=f"{crcl_range} mL/min",
    )
