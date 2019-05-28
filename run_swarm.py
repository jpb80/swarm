#!/usr/bin/env python
# coding=utf-8
"""
A docker swarm configuration tool.
"""
import subprocess
import click
import os
import logging
import sys


_log = logging.getLogger()
_log.setLevel(logging.INFO)

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.INFO)
formatter = logging.Formatter('### %(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
_log.addHandler(log_handler)


def _create_manager_machine(manager_name="manager", driver="virtualbox"):
    """
    Use docker-machine to create or start manager virtual machines (nodes).
    """
    try:
        subprocess.check_output(['docker-machine',
                                 'create',
                                 '--driver',
                                 driver,
                                 manager_name])
    except subprocess.CalledProcessError as ce:
        try:
            manager_ip = subprocess.check_output(['docker-machine',
                                                  'start',
                                                  manager_name])
        except subprocess.CalledProcessError as ce:
            manager_ip = subprocess.check_output(['docker-machine',
                                                  'ip', manager_name])
            pass
        pass


def _create_workers(worker_number=1,
                    worker_name="worker",
                    driver="virtualbox"):
    """
    Use docker-machine to create or start worker virutal machines (nodes).
    """
    worker_names = list()
    _log.info("Number of workers requested: %s", worker_number)
    while worker_number > 0:
        try:
            new_worker_name = worker_name + str(worker_number)
            _log.info("Attempting to create worker: %s", new_worker_name)
            subprocess.check_output(['docker-machine',
                                     'create',
                                     '--driver',
                                     driver,
                                     new_worker_name])
        except subprocess.CalledProcessError as ce:
            _log.info("Attempting to create worker failed, starting it: %s",
                      new_worker_name)
            try:
                subprocess.check_output(['docker-machine',
                                         'start',
                                         new_worker_name])
            except subprocess.CalledProcessError as ce:
                _log.info("Attempting to create worker failed, already running: %s",
                        new_worker_name)
                pass
        worker_names.append(new_worker_name)
        worker_number -= 1
    return worker_names


def _set_manager_env(machine="manager"):
    """
    Set DOCKER_ environment variables of the node for which commands will be
    run on.
    """
    _log.info("Set environment variables to allow running commands over ssh.")
    results = subprocess.check_output(['docker-machine', 'env', machine])
    _log.info("env manager: %s", results)
    results = results.decode().strip().split('\n')
    results = [i.replace("export ", "") for i in results if not "#" in i]
    for env in results:
        env = env.split("=")
        os.environ[env[0].replace('"', '')] = env[1].replace('"', '')

    _log.info("list all envs: %s", os.environ)


def create_private_registry(publish_ports="5000:5000",
                            reg_name="registry",
                            reg_addr="0.0.0.0:5000",
                            service_tag="registry:latest",
                            docker_image_tag="127.0.0.1:5000/swimage:latest",
                            dockerfile_path="."):
    """
    Create private docker image registry.  Allows sharing of images on all
    nodes.
    """
    _set_manager_env(machine="manager")

    _log.info("Creating private registry")
    worker_ip = subprocess.check_output(['docker',
                                         'service',
                                         'create',
                                         '--name',
                                         reg_name,
                                         '--publish=' + publish_ports,
                                         '-e',
                                         reg_addr,
                                         service_tag])

    subprocess.check_output(['docker',
                             'build',
                             '-t',
                             docker_image_tag,
                             dockerfile_path])

    subprocess.check_output(['docker',
                             'push',
                             docker_image_tag])


def init_machines(worker_number, manager_name="manager"):
    """
    Initialize all machines in this swarm.
    """
    _create_manager_machine(manager_name)
    manager_ip = _get_machine_ip(manager_name)
    _log.info("manager_ip: %s", manager_ip)
    worker_names = _create_workers(worker_number=worker_number)
    _log.info("Created workers: %s", worker_names)
    return manager_ip, worker_names


def _get_machine_ip(manager_name):
    """
    Use docker-machine to retrieve machine ip.
    """
    machine_ip = subprocess.check_output(['docker-machine', 'ip', manager_name])
    return machine_ip.decode().strip()

def init_swarm_manager(manager_ip):
    """
    Initialize a swarm manager on the given virtual machine.
    """
    _set_manager_env(machine="manager")

    subprocess.check_output(['docker',
                             'swarm',
                             'init',
                             '--advertise-addr',
                             manager_ip])

    join_token = subprocess.check_output(['docker',
                                          'swarm',
                                          'join-token',
                                          'worker',
                                          '-q'])

    join_token = join_token.decode().strip()
    _log.info("swarm join token: %s", join_token)
    return join_token


def init_swarm_workers(worker_names, join_token, manager_ip):
    """
    Initialize a number of swarm workers on virtual machines.
    """
    for worker_name in worker_names:
        _set_manager_env(machine=worker_name)
        subprocess.check_output(['docker',
                                 'swarm',
                                 'join',
                                 '--token',
                                 join_token,
                                 manager_ip + ':2377'])


def deploy_container_image_to_swarm(stack_name="stack"):
    """
    Use docker stack to deploy docker-compose configurations across all nodes
    in the swarm. Creates tasks running containers per node.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    _log.info("directory path: %s", dir_path)
    _set_manager_env(machine="manager")
    docker_compose_path = dir_path + "/docker-compose.yml"
    result = subprocess.check_output(['docker',
                                      'stack',
                                      'deploy',
                                      '--compose-file',
                                      docker_compose_path,
                                      stack_name])
    _log.info("deploy stack status: %s", result)


def scale_swarm_replicas(service_id='stack_web', number_of_tasks=0):
    """
    Scale swarm tasks on the nodes.
    """
    _set_manager_env(machine="manager")
    subprocess.check_output(['docker',
                             'service',
                             'scale',
                             service_id + "=" + number_of_tasks])


def _leave_swarm(machine):
    """
    Have the swarm leave the machine.
    """
    try:
        _set_manager_env(machine=machine)
        subprocess.check_output(['docker',
                                 'swarm',
                                 'leave',
                                 '--force'])
    except subprocess.CalledProcessError as ce:
        pass


def _get_nodes_hostnames(manager_name):
    """
    Get hostnames of nodes in the swarm service.
    """
    try:
        _set_manager_env(machine=manager_name)
        results = subprocess.check_output(['docker', 
                                           'node',
                                           'ls',
                                           '--format',
                                           '{{.Hostname}}'])
        return results.decode().split('\n').strip()
    except subprocess.CalledProcessError as ce:
        pass


def nuke_it(manager_name="manager", nuke_vms=False):
    """
    Remove all swarm tasks from nodes. Optional to delete all virtual
    machines.
    """
    #TODO:_get_nodes_hostnames(manager_name)
    worker_names = ["worker5", "worker4", "worker3", "worker2", "worker1"]
    for worker_name in worker_names:
        _log.info("Leaving swarm: %s", worker_name)
        _leave_swarm(machine=worker_name)
        if nuke_vms:
            _log.info("Removing vm: %s", worker_name)
            subprocess.check_output(['docker-machine',
                                     'rm',
                                     worker_name])

    _log.info("Manager leaving swarm: %s", manager_name)
    _leave_swarm(machine=manager_name)
    if nuke_vms:
        _log.info("Removing vm: %s", manager_name)
        subprocess.check_output(['docker-machine',
                                 'rm',
                                 manager_name])


@click.command()
@click.option('--worker_number',
              help='Set the number of worker nodes')
@click.option('--init',
              help='initalize the swarm',
              default=False)
@click.option('--scale',
              help='Scale the number of tasks in the swarm',
              default=False)
@click.option('--scale_number',
              help='Scale the number of tasks in the swarm')
@click.option('--remove_all',
              help='Remove all swarm nodes from vms',
              default=False)
def main(worker_number, init, scale, scale_number, remove_all):
    """
    Application for initializing, scaling, and removing nodes from a swarm.
    """
    if init:
        _log.info("Initializing all machines...")
        manager_ip, worker_names = init_machines(worker_number=int(worker_number))

        _log.info("Initializing swarm manager...")
        join_token = init_swarm_manager(manager_ip=manager_ip)


        _log.info("Joining workers to swarm...")
        init_swarm_workers(worker_names=worker_names,
                           join_token=join_token,
                           manager_ip=manager_ip)

        _log.info("Creating private registry...")
        create_private_registry()

        _log.info("Deploying container image to swarm...")
        deploy_container_image_to_swarm()
    elif scale:
        scale_swarm_replicas(number_of_tasks=scale_number)
    elif remove_all and not init and not scale:
        nuke_it()


if __name__ == '__main__':
    main()
