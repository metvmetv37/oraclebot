import oci
import time
import sys
import os

COMPARTMENT_ID = "ocid1.tenancy.oc1..aaaaaaaai5gfitc32oam4gur5msnrng6txlhy6benqeinxyt4dyqap3slnmq"
SUBNET_ID = "ocid1.subnet.oc1.us-chicago-1.aaaaaaaa2dbw6wkirwzvd5setknru2hre6hglacik6v5k3dne23dvmzjxjeq"
DISPLAY_NAME = "arm-free-vm"

# Sadece geçerli olan iki boyut taranacak
CONFIG_OPTIONS = [
    {"ocpus": 2, "memory": 12},
    {"ocpus": 1, "memory": 6}
]

# İşletim sistemine göre config yolunu otomatik seç (Windows veya Linux/Actions)
if os.name == 'nt':
    config_path = "C:\\Users\\EMİRHAN\\.oci\\config"
else:
    config_path = os.path.expanduser("~/.oci/config")

try:
    config = oci.config.from_file(file_location=config_path)
    compute_client = oci.core.ComputeClient(config)
    identity_client = oci.identity.IdentityClient(config)
except Exception as e:
    print(f"Config dosyası okunamadı! Hata: {e}")
    sys.exit(1)

print("Oracle Cloud ARM Sunucu Yakalama Botu Başlatıldı...")

try:
    ads = identity_client.list_availability_domains(compartment_id=COMPARTMENT_ID).data
    AVAILABILITY_DOMAIN = ads[0].name
    print(f"Kullanılacak Availability Domain: {AVAILABILITY_DOMAIN}")

    images = compute_client.list_images(
        compartment_id=COMPARTMENT_ID,
        operating_system="Canonical Ubuntu",
        operating_system_version="22.04",
        shape="VM.Standard.A1.Flex",
        sort_by="TIMECREATED",
        sort_order="DESC"
    ).data
    
    if not images:
        images = compute_client.list_images(
            compartment_id=COMPARTMENT_ID,
            shape="VM.Standard.A1.Flex",
            sort_by="TIMECREATED",
            sort_order="DESC"
        ).data

    IMAGE_ID = images[0].id
    print(f"Seçilen İmaj ID: {IMAGE_ID}\n")
except Exception as e:
    print(f"AD veya İmaj otomatik alınamadı: {e}")
    sys.exit(1)

print("Boş kapasite aranıyor, 2 OCPU ve 1 OCPU seçenekleri sırayla taranacak...\n")

while True:
    for opt in CONFIG_OPTIONS:
        current_ocpus = opt["ocpus"]
        current_memory = opt["memory"]
        
        try:
            launch_details = oci.core.models.CreateVnicDetails(
                subnet_id=SUBNET_ID,
                assign_public_ip=True
            )

            shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=current_ocpus,
                memory_in_gbs=current_memory
            )

            instance_details = oci.core.models.LaunchInstanceDetails(
                compartment_id=COMPARTMENT_ID,
                availability_domain=AVAILABILITY_DOMAIN,
                display_name=f"{DISPLAY_NAME}-{current_ocpus}c",
                shape="VM.Standard.A1.Flex",
                image_id=IMAGE_ID,
                shape_config=shape_config,
                create_vnic_details=launch_details
            )

            response = compute_client.launch_instance(instance_details)
            print(f"\nTebrikler! {current_ocpus} OCPU / {current_memory} GB RAM sunucu başarıyla yakalandı!")
            print(response.data)
            sys.exit(0)

        except oci.exceptions.ServiceError as e:
            if e.status == 429:
                print(f"[{current_ocpus}C Rate Limit (429)] Bekleniyor...", end="", flush=True)
                time.sleep(30)
            elif e.status == 500 or "Out of host capacity" in str(e) or "OutOfCapacity" in str(e):
                print(f"[{current_ocpus}C] .", end="", flush=True)
            elif "service limits were exceeded" in str(e).lower():
                print(f"[{current_ocpus}C Limit] x", end="", flush=True)
            else:
                print(f"\n[{current_ocpus}C Hata]: {e.message} (Kod: {e.status})")
            
            time.sleep(10)
            
    time.sleep(30)
