#################################################################
#
# Generate SBOA image
#
# Written by DEIMOS Space S.L. (dibb)
#
# module sboa
#################################################################

USAGE="Usage: `basename $0` -e path_to_eboa_src -v path_to_vboa_src -d path_to_dockerfile -p path_to_dockerfile_pkg -o path_to_orc_packets -f path_to_eopcfi -u uid_host_user_to_map -t path_to_tailored -b path_to_common_base [-a app] [-c boa_tailoring_configuration_path] [-l version]"

########
# Initialization
########
PATH_TO_EBOA=""
PATH_TO_VBOA=""
PATH_TO_TAILORED=""
PATH_TO_COMMON_BASE=""
COMMON_BASE_FOLDER=""
PATH_TO_DOCKERFILE="Dockerfile"
APP="vboa"
PATH_TO_ORC=""
VERSION="0.1.0"
UID_HOST_USER_TO_MAP=""

while getopts e:v:d:t:b:a:o:c:p:l:f:u: option
do
    case "${option}"
        in
        e) PATH_TO_EBOA=${OPTARG}; PATH_TO_EBOA_CALL="-e ${OPTARG}";;
        v) PATH_TO_VBOA=${OPTARG}; PATH_TO_VBOA_CALL="-v ${OPTARG}";;
        t) PATH_TO_TAILORED=${OPTARG}; PATH_TO_TAILORED_CALL="-t ${OPTARG}";;
        b) PATH_TO_COMMON_BASE=${OPTARG}; COMMON_BASE_FOLDER=`basename $PATH_TO_COMMON_BASE`; PATH_TO_COMMON_BASE_CALL="-b ${OPTARG}";;
        d) PATH_TO_DOCKERFILE=${OPTARG}; PATH_TO_DOCKERFILE_CALL="-d ${OPTARG}";;
        p) PATH_TO_DOCKERFILE_PKG=${OPTARG}; PATH_TO_DOCKERFILE_PKG_CALL="-p ${OPTARG}";;
        a) APP=${OPTARG}; APP_CALL="-a ${OPTARG}";;
        o) PATH_TO_ORC=${OPTARG}; PATH_TO_ORC_CALL="-o ${OPTARG}";;
        c) PATH_TO_BOA_TAILORING_CONFIGURATION=${OPTARG}; PATH_TO_BOA_TAILORING_CONFIGURATION_CALL="-c ${OPTARG}";;
        u) UID_HOST_USER_TO_MAP=${OPTARG}; UID_HOST_USER_TO_MAP_CALL="-u ${OPTARG}";;        
        l) VERSION=${OPTARG}; VERSION_CALL="-l ${OPTARG}";;
        f) PATH_TO_EOPCFI=${OPTARG};;
        ?) echo -e $USAGE
            exit -1
    esac
done

# Check that option -t has been specified
if [ "$PATH_TO_TAILORED" == "" ];
then
    echo "ERROR: The option -t has to be provided"
    echo $USAGE
    exit -1
fi

# Check that the path to the tailored exists
if [ ! -d $PATH_TO_TAILORED ];
then
    echo "ERROR: The directory $PATH_TO_TAILORED provided does not exist"
    exit -1
fi

# Check that option -b has been specified
if [ "$PATH_TO_COMMON_BASE" == "" ];
then
    echo "ERROR: The option -b has to be provided"
    echo $USAGE
    exit -1
fi

# Check that the path to the common base exists
if [ ! -d $PATH_TO_COMMON_BASE ];
then
    echo "ERROR: The directory $PATH_TO_COMMON_BASE provided does not exist"
    exit -1
fi

# Check that option -f has been specified
if [ "$PATH_TO_EOPCFI" == "" ];
then
    echo "ERROR: The option -f has to be provided"
    echo $USAGE
    exit -1
fi

# Check that the path to the eopcfi exists
if [ ! -d $PATH_TO_EOPCFI ];
then
    echo "ERROR: The directory $PATH_TO_EOPCFI provided does not exist"
    exit -1
fi

# Check libraries
for library in "libexplorer_data_handling.a" "libexplorer_file_handling.a" "libexplorer_lib.a" "libexplorer_orbit.a" "libexplorer_pointing.a" "libexplorer_visibility.a" "libgeotiff.a" "libproj.a" "libtiff.a" "libxml2.a";
do
    # Check that the library is present
    library_count=$(find $PATH_TO_EOPCFI/lib -maxdepth 1 -mindepth 1 -name $library | wc -l)
    if [ $library_count == 0 ];
    then
        echo "ERROR: The library $PATH_TO_EOPCFI/lib/$library does not exist in the provided eopcfi directory"
        exit -1
    fi
done

# Check header files
for header in "explorer_data_handling.h" "explorer_file_handling.h" "explorer_lib.h" "explorer_orbit.h" "explorer_pointing.h" "explorer_visibility.h";
do
    # Check that the header is present
    header_count=$(find $PATH_TO_EOPCFI/include -maxdepth 1 -mindepth 1 -name $header | wc -l)
    if [ $header_count == 0 ];
    then
        echo "ERROR: The header $PATH_TO_EOPCFI/include/$header does not exist in the provided eopcfi directory"
        exit -1
    fi
done

# Check binary files
for binary in "gen_pof";
do
    # Check that the binary is present
    binary_count=$(find $PATH_TO_EOPCFI/bin -maxdepth 1 -mindepth 1 -name $binary | wc -l)
    if [ $binary_count == 0 ];
    then
        echo "ERROR: The binary $PATH_TO_EOPCFI/bin/$binary does not exist in the provided eopcfi directory"
        exit -1
    fi
done

APP_CONTAINER="boa_app_$APP"

while true; do
read -p "
Welcome to the docker image generator of the $APP environment :-)

You are going to generate the docker image for the app: $APP...
These are the specific configuration options that will be applied to initialize the environment:
- PATH_TO_EOPCFI: $PATH_TO_EOPCFI

Do you wish to proceed with the generation of the docker image?" answer
    case $answer in
        [Yy]* )
            break;;
        [Nn]* )
            echo "No worries, the docker image will not be generated";
            exit;;
        * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
    esac
done

# Generate docker image
$PATH_TO_VBOA/generate_docker_image.sh $PATH_TO_EBOA_CALL $PATH_TO_VBOA_CALL $PATH_TO_TAILORED_CALL $PATH_TO_COMMON_BASE_CALL $PATH_TO_DOCKERFILE_CALL $PATH_TO_DOCKERFILE_PKG_CALL $APP_CALL $PATH_TO_ORC_CALL $PATH_TO_BOA_TAILORING_CONFIGURATION_CALL $UID_HOST_USER_TO_MAP_CALL $VERSION_CALL

# Check that the BOA image could be generated
status=$?
if [ $status -ne 0 ]
then
    echo "The BOA image could not be generated :-("
    exit -1
else
    echo "The BOA image has been generated successfully :-)"
fi

# Include the EOP CFI
# Compile source
docker cp $PATH_TO_EOPCFI $APP_CONTAINER:/
docker exec -it -u root $APP_CONTAINER bash -c "chown boa:boa /eopcfi"

echo "Compiling EOPCFI..."

docker exec -it -u boa $APP_CONTAINER bash -c "gcc -Wno-deprecated -g -fpic -c -DSQLCA_STORAGE_CLASS=static -I /eopcfi/include/ /$COMMON_BASE_FOLDER/src/siboa/eop_cfi/get_footprint.c -o /tmp/get_footprint.o"

echo "Objetcs for the EOPCFI interface generated..."

docker exec -it -u boa $APP_CONTAINER bash -c "gcc /tmp/get_footprint.o -Wno-deprecated -g -I /eopcfi/include/ -L /eopcfi/lib/ -lexplorer_visibility -lexplorer_pointing -lexplorer_orbit -lexplorer_lib -lexplorer_data_handling -lexplorer_file_handling -lgeotiff -ltiff -lproj -lxml2 -lm -lc -fopenmp -o /scripts/get_footprint; rm /tmp/get_footprint.o"

# Check that the CFI could be compiled
status=$?
if [ $status -ne 0 ]
then
    echo "The EOP CFI could not be compiled :-("
    exit -1
else
    echo "The EOP CFI has been compiled successfully :-)"
fi

docker exec -it -u boa $APP_CONTAINER bash -c "cp /eopcfi/bin/* /scripts"

# Check that the binaries could be copied
status=$?
if [ $status -ne 0 ]
then
    echo "The EOP CFI binaries could not be copied :-("
    exit -1
else
    echo "The EOP CFI binaries has been copied successfully :-)"
fi

TMP_DIR=`mktemp -d`
# Docker commit and save image
docker commit $APP_CONTAINER boa:$VERSION
docker commit $APP_CONTAINER boa:latest
docker save boa > $TMP_DIR/boa.tar

echo "BOA image exported in: "$TMP_DIR/boa.tar

echo "Removing temporal docker container and image"

docker stop $APP_CONTAINER
docker rm $APP_CONTAINER
docker rmi -f $(docker images boa -q)
