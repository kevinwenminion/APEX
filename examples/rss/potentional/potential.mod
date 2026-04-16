# ------------------------ FORCE FIELDS ------------------------------
# DPA-3.1-3M fine-tuned
# --------------------------------------------------------------------

# Model fine-tuned from certain branch of DPA-3.1-3M
pair_style      deepmd frozen_model.pth
# If atom names (O H in this example) are not set in the pair_coeff command, the type_map defined by the training parameter will be used by default.
pair_coeff      * * O H

neigh_modify    every 1 delay 0 check no

# ------------------------ TYPE MAPPING ------------------------------
variable O   equal 1
variable H   equal 2


# ------------------------ MASSES (units metal: g/mol) ---------------
mass ${H}   1.0080       # Hydrogen
mass ${O}   15.999       # Oxygen

        
