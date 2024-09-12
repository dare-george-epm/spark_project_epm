
#Modify this docker for your needs
FROM openjdk:8-alpine

ARG SPARK_VERSION_ARG=3.1.2
ARG HADOOP_VERSION=3.3.1

ENV BASE_IMAGE      openjdk:8-alpine
ENV SPARK_VERSION   $SPARK_VERSION_ARG

ENV SPARK_HOME      /opt/spark
ENV HADOOP_HOME     /opt/hadoop
ENV PATH            $PATH:$SPARK_HOME/bin

RUN set -ex && \
    apk upgrade --no-cache && \
    apk --update add --no-cache bash tini libstdc++ glib gcompat libc6-compat linux-pam krb5 krb5-libs nss openssl wget sed curl && \
    rm /bin/sh && \
    ln -sv /bin/bash /bin/sh && \
    echo "auth required pam_wheel.so use_uid" >> /etc/pam.d/su && \
    chgrp root /etc/passwd && chmod ug+rw /etc/passwd && \
    # Removed the .cache to save space
    rm -rf /root/.cache && rm -rf /var/cache/apk/*

COPY binary/spark-${SPARK_VERSION}-bin-without-hadoop.tgz /spark-${SPARK_VERSION}-bin-without-hadoop.tgz
COPY binary/hadoop-${HADOOP_VERSION}.tar.gz /hadoop-${HADOOP_VERSION}.tar.gz

#Install Spark
RUN tar -xzf /spark-${SPARK_VERSION}-bin-without-hadoop.tgz -C /opt/ && \
    ln -s /opt/spark-${SPARK_VERSION}-bin-without-hadoop $SPARK_HOME && \
    rm -f /spark-${SPARK_VERSION}-bin-without-hadoop.tgz && \
    mkdir -p $SPARK_HOME/work-dir && \
    mkdir -p $SPARK_HOME/spark-warehouse

# Install Hadoop
RUN tar -xzf /hadoop-${HADOOP_VERSION}.tar.gz -C /opt/ && \
    ln -s /opt/hadoop-${HADOOP_VERSION} $HADOOP_HOME && \
    rm -f /hadoop-${HADOOP_VERSION}.tar.gz

ENV PATH="$SPARK_HOME/bin:$HADOOP_HOME/bin:$PATH"
ENV SPARK_DIST_CLASSPATH $HADOOP_HOME/etc/hadoop:$HADOOP_HOME/share/hadoop/common/lib/*:$HADOOP_HOME/share/hadoop/common/*:$HADOOP_HOME/share/hadoop/hdfs:$HADOOP_HOME/share/hadoop/hdfs/lib/*:$HADOOP_HOME/share/hadoop/hdfs/*:$HADOOP_HOME/share/hadoop/mapreduce/*:$HADOOP_HOME/share/hadoop/yarn:$HADOOP_HOME/share/hadoop/yarn/lib/*:$HADOOP_HOME/share/hadoop/yarn/*:$HADOOP_HOME/share/hadoop/tools/lib/*
ENV SPARK_CLASSPATH $HADOOP_HOME/etc/hadoop:$HADOOP_HOME/share/hadoop/common/lib/*:$HADOOP_HOME/share/hadoop/common/*:$HADOOP_HOME/share/hadoop/hdfs:$HADOOP_HOME/share/hadoop/hdfs/lib/*:$HADOOP_HOME/share/hadoop/hdfs/*:$HADOOP_HOME/share/hadoop/mapreduce/*:$HADOOP_HOME/share/hadoop/yarn:$HADOOP_HOME/share/hadoop/yarn/lib/*:$HADOOP_HOME/share/hadoop/yarn/*:$HADOOP_HOME/share/hadoop/tools/lib/*

RUN wget -O $SPARK_HOME/jars/hadoop-azure-${HADOOP_VERSION}.jar https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-azure/${HADOOP_VERSION}/hadoop-azure-${HADOOP_VERSION}.jar
RUN wget -O $SPARK_HOME/jars/hadoop-azure-datalake-${HADOOP_VERSION}.jar https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-azure-datalake/${HADOOP_VERSION}/hadoop-azure-datalake-${HADOOP_VERSION}.jar
RUN wget -O $SPARK_HOME/jars/azure-storage-7.0.0.jar https://repo1.maven.org/maven2/com/microsoft/azure/azure-storage/7.0.0/azure-storage-7.0.0.jar
RUN wget -O $SPARK_HOME/jars/azure-data-lake-store-sdk-2.3.6.jar https://repo1.maven.org/maven2/com/microsoft/azure/azure-data-lake-store-sdk/2.3.6/azure-data-lake-store-sdk-2.3.6.jar
RUN wget -O $SPARK_HOME/jars/azure-keyvault-core-1.0.0.jar https://repo1.maven.org/maven2/com/microsoft/azure/azure-keyvault-core/1.0.0/azure-keyvault-core-1.0.0.jar
RUN wget -O $SPARK_HOME/jars/geohash-1.4.0.jar https://repo1.maven.org/maven2/ch/hsr/geohash/1.4.0/geohash-1.4.0.jar

COPY /docker/entrypoint.sh /opt/
COPY dist/sparkbasics-*.egg /opt/
COPY src /opt/

RUN chmod +x /opt/*.sh

RUN apk update && \
    apk add --no-cache python3 py3-pip build-base python3-dev musl-dev && \
    pip3 install --upgrade pip && \
#    pip3 install /tmp/pydantic_core-2.20.1-pp310-pypy310_pp73-musllinux_1_1_x86_64.whl && \
#    pip3 install /tmp/pydantic-2.8.2-py3-none-any.whl && \
#    pip3 install /tmp/pydantic_settings-2.5.2-py3-none-any.whl && \
    pip3 install setuptools pydantic==1.9.2 pygeohash requests pyspark opencage python-geohash && \
    rm -rf /var/cache/apk/*


WORKDIR /opt/spark/work-dir
ENTRYPOINT [ "/opt/entrypoint.sh" ]

# Specify the User that the actual main process will run as
ARG spark_uid=185
USER ${spark_uid}