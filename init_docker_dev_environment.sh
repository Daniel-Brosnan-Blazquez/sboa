#################################################################
#
# Init docker environment of the sboa based on the script of vboa
#
# Written by DEIMOS Space S.L. (dibb)
#
# module sboa
#################################################################

USAGE="Usage: `basename $0` -e path_to_eboa_src -v path_to_vboa_src -d path_to_dockerfile -o path_to_orc_packets -u host_user_to_map -t path_to_tailored -b path_to_common_base -f path_to_eopcfi [-p port] [-l containers_label] [-a app] [-c boa_tailoring_configuration_path] [-s path_to_boa_certificates] [-n] [-r]\n
Where:\n
-s path_to_boa_certificates: Path to SSL certificates which names should be boa_certificate.pem and boa_key.pem\n
-n: disable DDBB port exposure (5432). Exposure of this port is needed for obtaining differences between data models
-r: disable removal available BOA images
"

########
# Initialization
########
PATH_TO_EBOA=""
PATH_TO_VBOA=""
PATH_TO_TAILORED=""
PATH_TO_COMMON_BASE=""
COMMON_BASE_FOLDER=""
PATH_TO_DOCKERFILE="Dockerfile.dev"
PORT="5000"
CONTAINERS_LABEL="dev"
APP="vboa"
PATH_TO_ORC=""
HOST_USER_TO_MAP=""
EXPOSE_DDBB_PORT="TRUE"
PATH_TO_BOA_CERTIFICATES=""
REMOVE_AVAILABLE_BOA_IMAGES="TRUE"

while getopts e:v:d:o:u:p:t:b:l:a:c:s:nrf: option
do
    case "${option}"
        in
        e) PATH_TO_EBOA=${OPTARG};;
        v) PATH_TO_VBOA=${OPTARG};;
        d) PATH_TO_DOCKERFILE=${OPTARG};;
        o) PATH_TO_ORC=${OPTARG};;
        u) HOST_USER_TO_MAP=${OPTARG};;
        p) PORT=${OPTARG};;
        t) PATH_TO_TAILORED=${OPTARG};;
        b) PATH_TO_COMMON_BASE=${OPTARG};COMMON_BASE_FOLDER=`basename $PATH_TO_COMMON_BASE`;;
        l) CONTAINERS_LABEL=${OPTARG};;
        a) APP=${OPTARG};;
        c) PATH_TO_BOA_TAILORING_CONFIGURATION=${OPTARG};;
        s) PATH_TO_BOA_CERTIFICATES=${OPTARG};;
        n) EXPOSE_DDBB_PORT="FALSE";;
        r) REMOVE_AVAILABLE_BOA_IMAGES="FALSE";;
        f) PATH_TO_EOPCFI=${OPTARG};;
        ?) echo -e $USAGE
            exit -1
    esac
done

# Check that option -o has been specified
if [ "$PATH_TO_EOPCFI" == "" ];
then
    echo "ERROR: The option -f has to be provided"
    echo -e $USAGE
    exit -1
fi

# Check that the path to the eopcfi exists
if [ ! -d $PATH_TO_EOPCFI ];
then
    echo "ERROR: The directory $PATH_TO_EOPCFI provided does not exist"
    exit -1
fi

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

# Check that the last folder of the path to the eopcfis is eopcfi
if [ "$(basename $PATH_TO_EOPCFI)" != "eopcfi" ];
then
    echo "ERROR: The last directory of the path $PATH_TO_EOPCFI should be eopcfi"
    exit -1
fi

while true; do
    read -p "
Welcome to the initializer of the $APP development environment :-)

You are trying to initialize a new development environment for the app: $APP...
These are the specific configuration options that will be applied to initialize the environment:
- PATH_TO_EOPCFI: $PATH_TO_EOPCFI
- PATH_TO_COMMON_BASE: $PATH_TO_COMMON_BASE

Do you wish to proceed with the initialization of the development environment?" answer

    case $answer in
        [Yy]* )
            break;;
        [Nn]* )
            echo "No worries, the initializer will not continue";
            exit;;
        * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
    esac
done

######
# FROM VBOA init_docker_dev_environment.sh file
######

# Check that option -e has been specified
if [ "$PATH_TO_EBOA" == "" ];
then
    echo "ERROR: The option -e has to be provided"
    echo -e $USAGE
    exit -1
fi

# Check that the path to the eboa project exists
if [ ! -d $PATH_TO_EBOA ];
then
    echo "ERROR: The directory $PATH_TO_EBOA provided does not exist"
    exit -1
fi

# Check that option -v has been specified
if [ "$PATH_TO_VBOA" == "" ];
then
    echo "ERROR: The option -v has to be provided"
    echo -e $USAGE
    exit -1
fi

# Check that the path to the vboa project exists
if [ ! -d $PATH_TO_VBOA ];
then
    echo "ERROR: The directory $PATH_TO_VBOA provided does not exist"
    exit -1
fi

# Check that option -o has been specified
if [ "$PATH_TO_ORC" == "" ];
then
    echo "ERROR: The option -o has to be provided"
    echo -e $USAGE
    exit -1
fi

# Check that the path to the orc packets exists
if [ ! -d $PATH_TO_ORC ];
then
    echo "ERROR: The directory $PATH_TO_ORC provided does not exist"
    exit -1
fi

# Check that the needed orc packets are present
minarc_count=$(find $PATH_TO_ORC/ -maxdepth 1 -mindepth 1 -name 'minarc*' | wc -l)
if [ $minarc_count == 0 ];
then
    echo "ERROR: The directory $PATH_TO_ORC does not contain a minarc packet"
    exit -1
elif [ $minarc_count -gt 1 ];
then
    echo "ERROR: The directory $PATH_TO_ORC contains more than one minarc packet"
    exit -1
fi
orc_count=$(find $PATH_TO_ORC/ -maxdepth 1 -mindepth 1 -name 'orc*' | wc -l)
if [ $orc_count == 0 ];
then
    echo "ERROR: The directory $PATH_TO_ORC does not contain a orc packet"
    exit -1
elif [ $orc_count -gt 1 ];
then
    echo "ERROR: The directory $PATH_TO_ORC contains more than one orc packet"
    exit -1
fi

# Check that option -d has been specified
if [ "$PATH_TO_DOCKERFILE" == "" ];
then
    echo "ERROR: The option -d has to be provided"
    echo -e $USAGE
    exit -1
fi

# Check that the docker file exists
if [ ! -f $PATH_TO_DOCKERFILE ];
then
    echo "ERROR: The file $PATH_TO_DOCKERFILE provided does not exist"
    exit -1
fi

# Check that the path to the tailored project exists
if [ "$PATH_TO_TAILORED" != "" ] && [ ! -d $PATH_TO_TAILORED ];
then
    echo "ERROR: The directory $PATH_TO_TAILORED provided does not exist"
    exit -1
fi

# Check that the path to the common base project exists
if [ "$PATH_TO_COMMON_BASE" != "" ] && [ ! -d $PATH_TO_TAILORED ];
then
    echo "ERROR: The directory $PATH_TO_COMMON_BASE provided does not exist"
    exit -1
fi

# Check that the path to the boa tailoring congiguration exists
if [ "$PATH_TO_BOA_TAILORING_CONFIGURATION" != "" ] && [ ! -d $PATH_TO_BOA_TAILORING_CONFIGURATION ];
then
    echo "ERROR: The directory $PATH_TO_BOA_TAILORING_CONFIGURATION provided does not exist"
    exit -1
fi

# Check that option -u has been specified
if [ "$HOST_USER_TO_MAP" == "" ];
then
    echo "ERROR: The option -u has to be provided"
    echo -e $USAGE
    exit -1
fi

# Check that the path to the MINARC archive folder exists
if [ ! id $HOST_USER_TO_MAP >/dev/null 2>&1 ];
then
    while true; do
        read -p "The user $HOST_USER_TO_MAP does not exist. Do you wish to create it and proceed with the new installation?" answer
        case $answer in
            [Yy]* )
                useradd -m $HOST_USER_TO_MAP
                break;;
            [Nn]* ) exit;;
            * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
        esac
    done
fi

# Check that the path to the orc packets exists
if [ "$PATH_TO_BOA_CERTIFICATES" != "" ] && ! [ -d $PATH_TO_BOA_CERTIFICATES ];
then
    echo "ERROR: The directory $PATH_TO_BOA_CERTIFICATES provided does not exist"
    exit -1
fi

# Check that the needed certificates are available
if [ "$PATH_TO_BOA_CERTIFICATES" != "" ] && ! [ -f $PATH_TO_BOA_CERTIFICATES/boa_certificate.pem ];
then
    echo "ERROR: A path to the certificates has been provided but the file $PATH_TO_BOA_CERTIFICATES/boa_certificate.pem does not exist"
    exit -1
fi
if [ "$PATH_TO_BOA_CERTIFICATES" != "" ] && ! [ -f $PATH_TO_BOA_CERTIFICATES/boa_key.pem ];
then
    echo "ERROR: A path to the certificates has been provided but the file $PATH_TO_BOA_CERTIFICATES/boa_key.pem does not exist"
    exit -1
fi

EBOA_RESOURCES_PATH="/eboa/src/config"
DATABASE_CONTAINER="boa_database_$CONTAINERS_LABEL"
APP_CONTAINER="boa_app_$CONTAINERS_LABEL"
DOCKER_NETWORK="boa_network_$CONTAINERS_LABEL"

while true; do
    read -p "
Welcome to the initializer of the BOA development environment :-)

You are trying to initialize a new development environment for the app: $APP...
These are the configuration options that will be applied to initialize the environment:
- PATH_TO_EBOA: $PATH_TO_EBOA
- PATH_TO_VBOA: $PATH_TO_VBOA
- PATH_TO_TAILORED: $PATH_TO_TAILORED
- PATH_TO_COMMON_BASE: $PATH_TO_COMMON_BASE
- PATH_TO_DOCKERFILE: $PATH_TO_DOCKERFILE
- PORT: $PORT
- CONTAINERS_LABEL: $CONTAINERS_LABEL
- APP: $APP
- PATH_TO_ORC: $PATH_TO_ORC
- PATH_TO_BOA_TAILORING_CONFIGURATION: $PATH_TO_BOA_TAILORING_CONFIGURATION
- HOST_USER_TO_MAP: $HOST_USER_TO_MAP
- PATH_TO_BOA_CERTIFICATES: $PATH_TO_BOA_CERTIFICATES
- EXPOSE_DDBB_PORT: $EXPOSE_DDBB_PORT
- REMOVE_AVAILABLE_BOA_IMAGES: $REMOVE_AVAILABLE_BOA_IMAGES

Do you wish to proceed with the initialization of the development environment?" answer
    case $answer in
        [Yy]* )
            break;;
        [Nn]* )
            echo "No worries, the initializer will not continue";
            exit;;
        * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
    esac
done

if [ "$(docker ps -a | grep -w $DATABASE_CONTAINER)" ];
then
    while true; do
        read -p "There has been detected a container with the same name: $DATABASE_CONTAINER. Do you wish to remove it and proceed with the new installation?" answer
        case $answer in
            [Yy]* )
                # Remove eboa database container if it already exists
                docker stop $DATABASE_CONTAINER
                docker rm $DATABASE_CONTAINER
                break;;
            [Nn]* ) exit;;
            * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
        esac
    done
fi

if [ "$(docker ps -a | grep -w $APP_CONTAINER)" ];
then
    while true; do
        read -p "There has been detected a container with the same name: $APP_CONTAINER. Do you wish to remove it and proceed with the new installation?" answer
        case $answer in
            [Yy]* )
                # Remove app image and container if it already exists
                docker stop $APP_CONTAINER
                docker rm $APP_CONTAINER

                break;;
            [Nn]* ) exit;;
            * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
        esac
    done
fi

if [ "$REMOVE_AVAILABLE_BOA_IMAGES" == "TRUE" ] && [ "$(docker images boa_$CONTAINERS_LABEL -q)" ];
then
    while true; do
        read -p "There has been detected a BOA image with the name: boa_$CONTAINERS_LABEL. Do you wish to remove it and proceed with the new installation?" answer
        case $answer in
            [Yy]* )
                # Remove app image
                docker rmi $(docker images boa_$CONTAINERS_LABEL -q)

                break;;
            [Nn]* ) exit;;
            * ) echo "Please answer Y or y for yes or N or n for no. Answered: $answer";;
        esac
    done
fi

######
# Create network
######
docker network inspect $DOCKER_NETWORK &>/dev/null || docker network create --driver bridge $DOCKER_NETWORK

######
# Create database container
######
# Execute container
# Check configuration of postgis/postgres with -> psql -U postgres -> show all;
if [ "$EXPOSE_DDBB_PORT" == "TRUE" ];
then
    docker run --shm-size 512M --network=$DOCKER_NETWORK -p 5432:5432 --name $DATABASE_CONTAINER -d mdillon/postgis -c 'max_connections=5000' -c 'max_locks_per_transaction=5000'
else
    docker run --shm-size 512M --network=$DOCKER_NETWORK --name $DATABASE_CONTAINER -d mdillon/postgis -c 'max_connections=5000' -c 'max_locks_per_transaction=5000'
fi

######
# Create APP container
######
find $PATH_TO_VBOA -name *pyc -delete
find $PATH_TO_EBOA -name *pyc -delete
if [ "$PATH_TO_TAILORED" != "" ];
then
    find $PATH_TO_TAILORED -name *pyc -delete
fi
if [ "$PATH_TO_COMMON_BASE" != "" ];
then
    find $PATH_TO_COMMON_BASE -name *pyc -delete
fi

HOST_UID_USER_TO_MAP=`id -u $HOST_USER_TO_MAP`

if [ "$(docker images boa_$CONTAINERS_LABEL -q)" ];
then
    echo -e "The image boa_$CONTAINERS_LABEL was already available. So, it is not going to be re-built."
else
    docker build --build-arg FLASK_APP=$APP --build-arg UID_HOST_USER=$HOST_UID_USER_TO_MAP --build-arg HOST_USER=$HOST_USER_TO_MAP --build-arg PATH_TO_BOA_CERTIFICATES=$PATH_TO_BOA_CERTIFICATES -t boa_$CONTAINERS_LABEL -f $PATH_TO_DOCKERFILE $PATH_TO_VBOA
fi

# Initialize the eboa database
if [ "$PATH_TO_TAILORED" != "" ] && [ "$PATH_TO_COMMON_BASE" != "" ];
then
    docker run -e EBOA_DDBB_HOST=$DATABASE_CONTAINER -e SBOA_DDBB_HOST=$DATABASE_CONTAINER -e MINARC_DATABASE_HOST=$DATABASE_CONTAINER -e ORC_DATABASE_HOST=$DATABASE_CONTAINER --shm-size 512M --network=$DOCKER_NETWORK -p $PORT:5001 -it --name $APP_CONTAINER -d -v $PATH_TO_EBOA:/eboa -v $PATH_TO_VBOA:/vboa -v $PATH_TO_TAILORED:/$APP -v $PATH_TO_COMMON_BASE:/$COMMON_BASE_FOLDER boa_$CONTAINERS_LABEL
elif [ "$PATH_TO_TAILORED" != "" ];
then
    docker run -e EBOA_DDBB_HOST=$DATABASE_CONTAINER -e SBOA_DDBB_HOST=$DATABASE_CONTAINER -e MINARC_DATABASE_HOST=$DATABASE_CONTAINER -e ORC_DATABASE_HOST=$DATABASE_CONTAINER --shm-size 512M --network=$DOCKER_NETWORK -p $PORT:5001 -it --name $APP_CONTAINER -d -v $PATH_TO_EBOA:/eboa -v $PATH_TO_VBOA:/vboa -v $PATH_TO_TAILORED:/$APP boa_$CONTAINERS_LABEL
else
    docker run -e EBOA_DDBB_HOST=$DATABASE_CONTAINER -e SBOA_DDBB_HOST=$DATABASE_CONTAINER -e MINARC_DATABASE_HOST=$DATABASE_CONTAINER -e ORC_DATABASE_HOST=$DATABASE_CONTAINER --shm-size 512M --network=$DOCKER_NETWORK -p $PORT:5001 -it --name $APP_CONTAINER -d -v $PATH_TO_EBOA:/eboa -v $PATH_TO_VBOA:/vboa boa_$CONTAINERS_LABEL
fi

# Link and copy configurations
for file in `find $PATH_TO_EBOA/src/config/ -name '*' -type f`;
do
    file_name=`basename $file`
    docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "ln -s /eboa/src/config/$file_name /resources_path/$file_name"
done
for file in `find $PATH_TO_VBOA/src/config/ -name '*' -type f`;
do
    file_name=`basename $file`
    docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "ln -s /vboa/src/config/$file_name /resources_path/$file_name"
done
#  (Change these operations to symbolic links)
for file in `find $PATH_TO_BOA_TAILORING_CONFIGURATION -name '*' -type f`;
do
    docker cp $file $APP_CONTAINER:/resources_path
done
for file in `find $PATH_TO_ORC -name '*' -type f`;
do
    docker cp $file $APP_CONTAINER:/orc_packages
done

# Copy BOA certificates for SSL connection
if [ "$PATH_TO_BOA_CERTIFICATES" != "" ];
then
    docker cp $PATH_TO_BOA_CERTIFICATES/boa_certificate.pem $APP_CONTAINER:/resources_path
    docker cp $PATH_TO_BOA_CERTIFICATES/boa_key.pem $APP_CONTAINER:/resources_path
fi

# Change ownership
docker exec -it -u root $APP_CONTAINER bash -c "chown $HOST_USER_TO_MAP:$HOST_USER_TO_MAP /resources_path/*"
docker exec -it -u root $APP_CONTAINER bash -c "chown $HOST_USER_TO_MAP:$HOST_USER_TO_MAP /orc_packages//*"

# Generate the python archive
docker exec -it -u root $APP_CONTAINER bash -c "pip3 install --upgrade pip"
docker exec -it -u root $APP_CONTAINER bash -c "pip3 install -e '/eboa/src[tests]'"
docker exec -it -u root $APP_CONTAINER bash -c "pip3 install -e '/vboa/src[tests]'"
if [ "$PATH_TO_TAILORED" != "" ];
then
    docker exec -it -u root $APP_CONTAINER bash -c "pip3 install -e /$APP/src"
fi
if [ "$PATH_TO_COMMON_BASE" != "" ];
then
    docker exec -it -u root $APP_CONTAINER bash -c "pip3 install -e /$COMMON_BASE_FOLDER/src"
fi

# Restart container to make accesible the app to the web server
docker restart $APP_CONTAINER

# Install web packages
docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "npm --prefix /vboa/src/vboa/static install"

# Install scripts
docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c 'for script in /eboa/src/scripts/*; do ln -s $script /scripts/`basename $script`; done'

# Link datamodels
docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c 'ln -s /eboa/datamodel/eboa_data_model.sql /datamodel/'
docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c 'ln -s /eboa/datamodel/sboa_data_model.sql /datamodel/'

# Install cron activities
echo "Installing cron activities"
docker exec -d -it -u root $APP_CONTAINER bash -c "cp /eboa/src/cron/boa_cron /etc/cron.d/"
if [ "$PATH_TO_TAILORED" != "" ] && [ -f "$PATH_TO_TAILORED/src/cron/boa_cron" ];
then
    docker exec -d -it -u root $APP_CONTAINER bash -c "cp /$APP/src/cron/boa_cron /etc/cron.d/"
fi

# Copy cron to crontab
docker exec -d -it -u root $APP_CONTAINER bash -c "crontab /etc/cron.d/boa_cron"

echo "Cron activities installed"

# Install orc
docker exec -it -u root $APP_CONTAINER bash -c "source scl_source enable rh-ruby25; cd /orc_packages/; gem install minarc*"
docker exec -it -u root $APP_CONTAINER bash -c "source scl_source enable rh-ruby25; cd /orc_packages/; gem install orc*"

# Initialize the EBOA database inside the postgis-database container
while true
do
    echo "Trying to initialize EBOA, SBOA, minArc and ORC databases..."
    docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "source scl_source enable rh-ruby25; eboa_init.py -o -s -y"
    status=$?
    if [ $status -ne 0 ]
    then
        echo "Server is not ready yet..."
        # Wait for the server to be initialize
        sleep 1
    else
        echo "Databases have been initialized... :D"
        break
    fi
done

# Execute the ORC server
docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "source scl_source enable rh-ruby25; orcBolg -c start"

#####
# End content extracted from init_docker_dev_environment.sh from VBOA
#####

# Check that the docker environment has been created correctly
status=$?
if [ $status -ne 0 ]
then
    echo "Docker environment could not be created :-("
    exit -1
else
    echo "Docker environment has been created successfully :-)"
fi

##################
# Install EOPCFI #
##################
APP_CONTAINER="boa_app_$CONTAINERS_LABEL"
# Compile source
docker cp $PATH_TO_EOPCFI $APP_CONTAINER:/

echo "Compiling EOPCFI..."

docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "gcc -Wno-deprecated -g -fpic -c -DSQLCA_STORAGE_CLASS=static -I /eopcfi/include/ /$COMMON_BASE_FOLDER/src/sboa/eop_cfi/get_footprint.c -o /tmp/get_footprint.o"

echo "Objetcs for the EOPCFI interface generated..."

docker exec -it -u $HOST_USER_TO_MAP $APP_CONTAINER bash -c "gcc /tmp/get_footprint.o -Wno-deprecated -g -I /eopcfi/include/ -L /eopcfi/lib/ -lexplorer_visibility -lexplorer_pointing -lexplorer_orbit -lexplorer_lib -lexplorer_data_handling -lexplorer_file_handling -lgeotiff -ltiff -lproj -lxml2 -lm -lc -fopenmp -o /scripts/get_footprint; rm /tmp/get_footprint.o"

# Check that the CFI could be compiled
status=$?
if [ $status -ne 0 ]
then
    echo "The EOP CFI could not be compiled :-("
    exit -1
else
    echo "The EOP CFI has been compiled successfully :-)"
fi

echo "
The development environment for $APP has been initialized :-)"